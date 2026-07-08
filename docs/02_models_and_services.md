# 2. Models & Services In Detail

This system relies on a diverse stack of open-source, state-of-the-art machine learning models. Each is optimized to run purely on the CPU to eliminate the need for expensive AWS GPU instances.

## Audio Processing Pipeline

1. **Faster-Whisper (CTranslate2)**
   - **Purpose**: Speech-to-text transcription.
   - **How it works**: Uses a heavily quantized (compressed) version of OpenAI's Whisper model. It runs on the CPU backend much faster than standard PyTorch Whisper.
   - **Service Layer**: Extracts the transcribed text to be analyzed for prohibited keywords or verification scripts.

2. **Pyannote Audio**
   - **Purpose**: Speaker Diarization.
   - **How it works**: Analyzes the audio waveform to identify distinct vocal signatures and maps out overlapping speech segments.
   - **Service Layer**: Ensures that a KYC audio recording contains exactly one speaker, failing the check if multiple voices are detected.

3. **SpeechBrain (ECAPA-TDNN)**
   - **Purpose**: Voice Embeddings & Biometrics.
   - **How it works**: Extracts a mathematical representation of a voice (an embedding) that can be compared against known bad actors or used to verify identity across multiple recordings.

4. **PANNs (Pre-trained Audio Neural Networks)**
   - **Purpose**: Audio Event Classification.
   - **How it works**: Detects non-speech events (e.g., sirens, typing, background noise) to provide context on the recording environment.

## Visual & Photo Pipeline

1. **InsightFace**
   - **Purpose**: Face Detection and Recognition.
   - **How it works**: A highly accurate face analysis library used to detect facial landmarks, bounding boxes, and extract facial embeddings. It verifies that a face is present, front-facing, and matches ID records.

2. **NudeNet**
   - **Purpose**: NSFW and Explicit Content Filtering.
   - **How it works**: A classification model that scans image pixels or video frames to detect nudity, violence, or prohibited objects, ensuring uploaded media is safe for processing.

3. **MediaPipe (Google)**
   - **Purpose**: Lightweight Vision Tasks.
   - **How it works**: Used as an extremely fast pre-filter for structural analysis (e.g., detecting if an image is completely blank or corrupt) before passing the image to the heavier models like InsightFace.

## Service Integration

The `app/services/` directory is split into `audio/` and `photo/` modules. Each module maintains its own **Worker Pool** (`ProcessPoolExecutor`). 

When a request arrives at the FastAPI router:
1. The request payload is dumped into bytes.
2. The bytes are sent via `asyncio.get_running_loop().run_in_executor()` to an isolated Python process.
3. The isolated process loads the required model, performs the inference, and returns the JSON result.
4. If a model crashes inside the worker, the main FastAPI server survives and simply restarts the dead worker process.
