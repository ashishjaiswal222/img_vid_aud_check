import inspect
import warnings

# Suppress annoying third-party library tracebacks and warnings on fresh clones
warnings.filterwarnings("ignore", category=UserWarning, module="pyannote.audio.core.io")
warnings.filterwarnings("ignore", category=UserWarning, module="speechbrain")
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pydub.utils")

original_getframeinfo = inspect.getframeinfo
def patched_getframeinfo(frame, context=1):
    info = original_getframeinfo(frame, context)
    if hasattr(info, 'filename') and info.filename.endswith("\\inspect.py"):
        return inspect.Traceback(info.filename.replace("\\inspect.py", "/inspect.py"), info.lineno, info.function, info.code_context, info.index)
    return info
inspect.getframeinfo = patched_getframeinfo

import torch
from faster_whisper import WhisperModel
import speechbrain.inference
from pyannote.audio import Pipeline

import os
import urllib.request
# Fix panns_inference bug on fresh installs where it crashes on import if CSV is missing
panns_dir = os.path.join(os.path.expanduser('~'), 'panns_data')
os.makedirs(panns_dir, exist_ok=True)
csv_path = os.path.join(panns_dir, 'class_labels_indices.csv')
if not os.path.exists(csv_path):
    print("Downloading PANNS class labels...")
    url = "https://raw.githubusercontent.com/qiuqiangkong/audioset_tagging_cnn/master/metadata/class_labels_indices.csv"
    try:
        urllib.request.urlretrieve(url, csv_path)
    except Exception as e:
        print(f"Failed to download panns class labels: {e}")

# Fix panns_inference 'wget' missing error on Windows by downloading the weights natively
pth_path = os.path.join(panns_dir, 'Cnn14_mAP=0.431.pth')

# Check if file exists and is actually a valid PyTorch model. If corrupted/partial, remove it.
if os.path.exists(pth_path):
    try:
        import torch
        # A quick peek to see if it's truncated/corrupted
        torch.load(pth_path, map_location='cpu')
    except Exception:
        print("Detected corrupted PANNS model weights. Removing...")
        os.remove(pth_path)

if not os.path.exists(pth_path):
    print("Downloading PANNS model weights (this might take a minute)...")
    url = "https://zenodo.org/record/3987831/files/Cnn14_mAP%3D0.431.pth?download=1"
    try:
        # Download to a temporary file first to prevent corruption from interrupted downloads
        tmp_path = pth_path + ".tmp"
        urllib.request.urlretrieve(url, tmp_path)
        os.rename(tmp_path, pth_path)
    except Exception as e:
        print(f"Failed to download panns model weights: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

import panns_inference
from app.config import settings
from app.services.audio.constants import WHISPER_MODEL_SIZE

_MODELS = {
    "vad": None,
    "vad_utils": None,
    "whisper": None,
    "ecapa": None,
    "panns": None,
    "pyannote": None
}

def init_worker_models():
    """
    Initializes models once per worker process.
    """
    global _MODELS
    
    # Prevent OpenMP thread contention crash in Windows ProcessPoolExecutor
    torch.set_num_threads(1)
    
    from filelock import FileLock
    models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")
    os.makedirs(models_dir, exist_ok=True)
    global_lock_path = os.path.join(models_dir, "audio_models_download.lock")
    
    with FileLock(global_lock_path):
        # 1. Silero VAD
        vad_model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                          model='silero_vad',
                                          force_reload=False,
                                          trust_repo=True,
                                          onnx=True)
        _MODELS["vad"] = vad_model
        _MODELS["vad_utils"] = utils
    
        # 2. Faster Whisper
        _MODELS["whisper"] = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
        
        # 3. SpeechBrain ECAPA-TDNN
        # Ensure models save to an absolute path so it works regardless of where the server is run from
        speechbrain_dir = os.path.join(models_dir, "spkrec-ecapa-voxceleb")
        _MODELS["ecapa"] = speechbrain.inference.SpeakerRecognition.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb", 
            savedir=speechbrain_dir
        )
        
        # 4. PANNs
        _MODELS["panns"] = panns_inference.AudioTagging(checkpoint_path=None, device='cpu')
        
        # 5. Pyannote Overlapped Speech
        if not settings.use_overlap_heuristic_fallback and settings.hf_token:
            try:
                pipeline = Pipeline.from_pretrained(
                    "pyannote/overlapped-speech-detection",
                    use_auth_token=settings.hf_token
                )
                _MODELS["pyannote"] = pipeline
            except Exception:
                _MODELS["pyannote"] = None
        else:
            _MODELS["pyannote"] = None

    # 6. Warmup Inference
    try:
        import structlog
        logger = structlog.get_logger()
        logger.info("Warming up models...")
        import numpy as np
        # 1-second dummy audio at 16kHz
        dummy_audio = np.zeros(16000, dtype=np.float32)
        
        # Silero VAD Warmup
        tensor = torch.from_numpy(dummy_audio).float()
        _MODELS["vad_utils"][0](tensor, _MODELS["vad"], sampling_rate=16000)
        
        # Whisper Warmup
        _MODELS["whisper"].transcribe(dummy_audio, beam_size=1)
        
        # SpeechBrain Warmup
        _MODELS["ecapa"].encode_batch(tensor.unsqueeze(0))
        
        # PANNs Warmup
        batch = dummy_audio[None, :]
        _MODELS["panns"].inference(batch)
        
        logger.info("Models warmup complete.")
    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        logger.warning("Warmup failed, but models loaded.", error=str(e))

def get_models():
    return _MODELS
