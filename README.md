# Unified AI Verification API

This repository contains a monolithic FastAPI microservice that consolidates Video Moderation, Audio Verification, and Photo KYC Verification into a single, high-performance deployment. It utilizes multiprocessing to manage CPU-intensive AI inferences (Whisper, InsightFace, NudeNet, Pyannote, etc.) without blocking the core event loop.

## Prerequisites

- **Python**: 3.10 to 3.12 (Do **not** use 3.13 or 3.14 as PyTorch/Torchaudio do not fully support them yet).
- **OS**: Windows, macOS, or Linux.
- **FFmpeg**: Required for audio processing, but handled automatically via setup scripts.

---

## Local Development Setup

We have provided simple bootstrap scripts to automatically handle your local environment, install dependencies, and download necessary binaries (like FFmpeg).

### 1. Clone the repository
```bash
git clone https://github.com/ashishjaiswal222/img_vid_aud_check.git
cd img_vid_aud_check
```

### 2. Run the Bootstrap Script
**On Windows:**
```powershell
# Open PowerShell and run:
.\setup.bat
```

**On Linux / macOS:**
```bash
bash setup.sh
```

*(This script will create a virtual environment, install all `requirements.txt` dependencies safely, download FFmpeg into a local `bin/` directory, and generate a `.env` file).*

### Alternative: Manual Setup
If you prefer not to use the automated scripts, you can manually configure your environment:
```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use: .\venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup local FFmpeg
python scripts/install_ffmpeg.py

# 4. Create your environment file
cp .env.example .env      # On Windows use: copy .env.example .env
```

### 3. Configure `.env`
Open the newly created `.env` file in the root directory and fill in the required values (like your HuggingFace token and AWS credentials).

### 4. Start the Server
Do **not** run `python main.py` directly. You must start the server using the Uvicorn ASGI server.

```bash
# Ensure your virtual environment is active, then run:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*(Note: On the first boot, the server will automatically download necessary AI models like `blaze_face_short_range.tflite` to `app/models/`. This might take a few minutes).*

---

## Production Deployment (Docker)

For production, this API is designed to run in a Docker container on AWS (or any cloud provider). The `Dockerfile` natively handles system-level dependencies like `libgl1` (for OpenCV) and `ffmpeg`.

### 1. Build the Docker Image
```bash
docker build -t unified-ai-api .
```

### 2. Run the Container
You must pass your `.env` variables to the container.
```bash
docker run -d --name ai-api -p 8000:8000 --env-file .env unified-ai-api
```

## API Documentation
Once the server is running, visit the interactive Swagger UI to test the endpoints:
- **Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### Available Routes:
- `/moderation/analyze`: Video/Image moderation
- `/moderation/audio-verify/check`: Audio verification (speaker count, overlap, clarity)
- `/moderation/photo-verify/check-single`: Photo KYC validation (blur, lighting, spoofing, identity matching)

---

## Video & Image Moderation — Nudity Detection Behaviour

The nudity detection engine (`app/services/nudity.py`) uses [NudeNet](https://github.com/notAI-tech/NudeNet) with the following tuned settings to avoid false positives on legitimate content like gym wear, swimwear, and sports clothing.

### What IS flagged (NSFW)
Only genuinely explicit exposure triggers a block:

| Label | Description |
|---|---|
| `FEMALE_GENITALIA_EXPOSED` | Explicit female genitalia |
| `MALE_GENITALIA_EXPOSED` | Explicit male genitalia |
| `ANUS_EXPOSED` | Explicit anus exposure |

### What is NOT flagged (Safe)
The following are intentionally excluded to prevent false positives:

| Label | Reason |
|---|---|
| `FEMALE_BREAST_EXPOSED` | Bikini tops / sports bras trigger this |
| `BUTTOCKS_EXPOSED` | Swimwear / gym shorts trigger this |
| `MALE_BREAST_EXPOSED` | Shirtless men are not nudity |
| `BELLY_EXPOSED` | Crop-tops, gym wear |
| `ARMPITS_EXPOSED` | Sleeveless clothes, open hands/arms |

### Key Tuning Parameters

| Constant | Value | Purpose |
|---|---|---|
| `DEFAULT_THRESHOLD` | `0.75` | Minimum confidence score per detection (higher = fewer false positives) |
| `COVERED_SUPPRESSION_THRESHOLD` | `0.55` | If a `_COVERED` counterpart label is detected alongside an `_EXPOSED` label, the exposed flag is suppressed (handles bikini/underwear edge cases) |
| `NUDE_FRAME_THRESHOLD` | `5` | **Video only** — minimum number of frames that must independently flag as nude before the video is marked NSFW. A single blurry or falsely-detected frame is ignored. |

### Video vs Image logic

- **Video**: Scans all extracted frames. Only marks NSFW if **5 or more frames** are detected as nude. Exits early once the threshold is reached.
- **Image**: Single image is flagged on **1 detection** above the confidence threshold (no frame averaging possible).
