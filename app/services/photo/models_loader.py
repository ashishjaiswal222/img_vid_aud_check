import os
import mediapipe as mp
import insightface
from insightface.app import FaceAnalysis
from nudenet import NudeDetector
import urllib.request
import structlog

logger = structlog.get_logger()

class MediaPipeModels:
    _instance = None

    def __init__(self):
        self.face_detector = None
        self.pose_landmarker = None
        self.face_landmarker = None
        self.image_segmenter = None
        self.face_analysis = None
        self.nude_detector = None
        self._load_models()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_model_exists(self, filepath: str, url: str):
        from filelock import FileLock
        lock_path = filepath + ".lock"
        with FileLock(lock_path):
            if not os.path.exists(filepath):
                logger.info(f"Downloading missing model...", model=os.path.basename(filepath))
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                tmp_path = filepath + ".tmp"
                try:
                    urllib.request.urlretrieve(url, tmp_path)
                    os.rename(tmp_path, filepath)
                    logger.info("Model downloaded successfully.", model=os.path.basename(filepath))
                except Exception as e:
                    logger.error("Model download failed.", error=str(e))
                    if os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass
                    raise

    def _load_models(self):
        models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")
        
        # 1. Face Detector
        fd_path = os.path.join(models_dir, "blaze_face_short_range.tflite")
        self._ensure_model_exists(fd_path, "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite")
        fd_options = mp.tasks.vision.FaceDetectorOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=fd_path),
            min_detection_confidence=0.5
        )
        self.face_detector = mp.tasks.vision.FaceDetector.create_from_options(fd_options)

        # 2. Pose Landmarker
        pl_path = os.path.join(models_dir, "pose_landmarker_lite.task")
        self._ensure_model_exists(pl_path, "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task")
        pl_options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=pl_path),
            output_segmentation_masks=False
        )
        self.pose_landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(pl_options)

        # 3. Face Landmarker (with blendshapes and iris)
        fl_path = os.path.join(models_dir, "face_landmarker.task")
        self._ensure_model_exists(fl_path, "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task")
        fl_options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=fl_path),
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
            num_faces=1
        )
        self.face_landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(fl_options)

        # 4. Image Segmenter (Selfie Multiclass)
        seg_path = os.path.join(models_dir, "selfie_multiclass_256x256.tflite")
        self._ensure_model_exists(seg_path, "https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/float32/1/selfie_multiclass_256x256.tflite")
        seg_options = mp.tasks.vision.ImageSegmenterOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=seg_path),
            output_category_mask=True,
            output_confidence_masks=False
        )
        self.image_segmenter = mp.tasks.vision.ImageSegmenter.create_from_options(seg_options)

        from filelock import FileLock
        global_lock_path = os.path.join(models_dir, "insightface_nudenet_download.lock")
        with FileLock(global_lock_path):
            # 5. Identity Verification (InsightFace)
            # Note: This will download 'buffalo_l' models to ~/.insightface on first run if missing.
            self.face_analysis = FaceAnalysis(
                name='buffalo_l', 
                allowed_modules=['detection', 'recognition'], 
                providers=['CPUExecutionProvider']
            )
            self.face_analysis.prepare(ctx_id=0, det_size=(480, 480))
    
            # 6. Explicit Content (NudeNet)
            # Note: This downloads the default model (~80MB) to ~/.NudeNet on first run if missing.
            self.nude_detector = NudeDetector()

def get_models() -> MediaPipeModels:
    return MediaPipeModels.get_instance()
