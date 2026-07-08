# 3. Libraries & Tools

Below is a detailed breakdown of the critical libraries and system-level tools used to build and run this API.

## Core Infrastructure
- **FastAPI**: The asynchronous web framework handling HTTP routing, middleware (rate limiting, file size limits), and JSON serialization.
- **Uvicorn**: The ASGI server that runs the FastAPI application.
- **Pydantic**: Used for strict data validation and parsing JSON payloads into strongly-typed Python objects.
- **Python 3.11**: Chosen specifically as the execution environment because it provides the best compatibility matrix between modern typing features and stable C-extensions for machine learning libraries.

## ML Frameworks
- **PyTorch (CPU Only)**: The foundational tensor and neural network library. We strictly use `torch`, `torchvision`, and `torchaudio` versions compiled *without* CUDA to drastically reduce the Docker image size and prevent runtime crashes on CPU-only EC2 instances.
- **ONNXRuntime**: An engine for running models exported from PyTorch/TensorFlow. Used extensively by InsightFace and NudeNet.
- **NumPy & SciPy**: Core mathematical libraries used for matrix operations, audio signal manipulation, and image arrays.

## Media Processing
- **FFmpeg (System Tool)**: A critical system-level binary required to decode/encode audio and video files. Without FFmpeg, libraries like `pydub` and `torchaudio` cannot read `.mp4` or `.mp3` files.
- **ffmpeg-python**: Python bindings to execute FFmpeg commands directly from the code.
- **OpenCV (`opencv-python-headless`)**: Used for image manipulation (resizing, color conversions). The `-headless` version is used to avoid requiring X11 GUI system libraries (like `libSM.so`) on the Docker container.
- **Pillow (PIL)**: Standard image reading and manipulation library.
- **Librosa & Soundfile**: Used for reading audio files, extracting spectrograms, and analyzing audio sample rates.

## API Security & Utility
- **SlowAPI**: Implements IP-based rate limiting to protect the heavy ML endpoints from DDoS attacks or abuse.
- **Python-Multipart**: Required by FastAPI to parse `multipart/form-data` uploads (e.g., when a user uploads a `.jpg` or `.wav` file).
- **Structlog**: A structured logging library that forces all logs into a highly readable, parsable format (perfect for CloudWatch or Datadog).
