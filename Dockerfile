FROM python:3.11-slim

# Install system deps (FFmpeg for video/audio, libgl for OpenCV, libsndfile for torchaudio)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libavcodec-extra libgl1 libglib2.0-0 libsndfile1 libgles2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Ensure local modules can be imported
ENV PYTHONPATH=/app

RUN python -m pip install --upgrade pip setuptools wheel

# Copy dependencies
COPY requirements.txt ./

# Force PyTorch CPU installation first
RUN pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install the rest of the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Pre-download all AI models to bake them directly into the Docker image.
# We explicitly delete unused InsightFace sub-models to save ~150MB of Docker image space.
RUN python scripts/download_models.py && \
    rm -f ~/.insightface/models/buffalo_l/1k3d68.onnx \
    ~/.insightface/models/buffalo_l/2d106det.onnx \
    ~/.insightface/models/buffalo_l/genderage.onnx

# Expose the API port
EXPOSE 8000

# Start the application using Uvicorn ASGI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
