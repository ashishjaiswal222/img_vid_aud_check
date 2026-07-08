# 4. Production Deployment Guide

Deploying this monolithic ML API requires careful attention to compute resources, storage, and dependency management. Follow these guidelines to ensure a stable AWS EC2 deployment.

## 1. Instance Sizing & Hardware
This application loads multiple large neural networks into memory simultaneously. 
- **Minimum Recommended Instance**: `t3.large` or `t3.xlarge` (At least 8GB of RAM).
- **Why?**: The Whisper model alone requires ~1.5GB of RAM. Pyannote, SpeechBrain, and InsightFace require another 1-2GB. If you run multiple worker processes (e.g., `WORKER_POOL_SIZE = 2`), this memory requirement doubles.
- **Storage**: The root EBS volume should be at least **30GB**. The PyTorch CPU wheels are over 2GB, and the AI models downloaded on the first boot consume another 2-4GB. A full disk will cause silent crashes.

## 2. Docker Architecture

The application must be deployed using the provided `Dockerfile`. 

### The Build Process
```bash
docker build -t unified-ai-api .
```
During the build, the Dockerfile performs several critical steps:
1. **Base Image**: Uses `python:3.11-slim` for maximum stability and speed.
2. **System Dependencies**: Installs `ffmpeg`, `libgl1`, and `libsndfile1` via `apt-get`.
3. **Python Dependencies**: Uses a highly-strict `constraints.txt` file to lock PyTorch to CPU-only builds. 
4. **Model Pre-fetching**: Runs `scripts/download_models.py` to bake the AI weights directly into the Docker image. This guarantees sub-second startup times when the container boots in production, as it won't need to download gigabytes of data from HuggingFace on the fly.

### Running the Container
```bash
docker run -d --name ai-api \
    -p 8000:8000 \
    --restart unless-stopped \
    --env-file .env \
    unified-ai-api
```
- `--restart unless-stopped`: Ensures the API comes back online if the EC2 instance reboots.

## 3. Swap Space (Memory Buffer)
If you are deploying to an instance with exactly 8GB of RAM, you should configure a Swap file on the host machine as a safety net against OOM (Out of Memory) crashes during spike loads.

Run this on your EC2 Host (Ubuntu/Amazon Linux):
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## 4. Load Balancer Health Checks
If deploying behind an AWS Application Load Balancer (ALB):
- Point the health check to `/health`.
- **CRITICAL**: Set the Health Check Timeout to at least **120 seconds** and the interval to 30 seconds. On cold boots, loading all the ML models into memory can take 30 to 60 seconds. If the ALB timeout is too short, it will prematurely mark the instance as dead and terminate it in a loop.
