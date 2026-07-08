# Deployment / EC2 Notes

This service runs a heavy set of ML models including Whisper (for audio transcription), SpeechBrain (for audio embeddings), PANNs (audio classification), Pyannote (diarization), MediaPipe, and NudeNet.
When deploying on EC2, please follow these guidelines:

## 1. Instance Sizing & Memory (OOM Avoidance)
- **Minimum Recommended Instance**: `t3.large` or `t3.xlarge` (at least 8GB RAM). 
- Avoid `t2.micro` or `t3.micro`. The AI models alone consume 3-6GB RAM when loaded in memory.
- If using multiple worker processes (`WORKER_POOL_SIZE > 1`), RAM requirements multiply linearly. If on a single `t3.large`, strictly set `WORKER_POOL_SIZE=1`.
- **OOM Errors**: If the container silently restarts, check `dmesg -T | grep -i "killed process"` or `journalctl -k | grep oom` on the host to verify if the OOM killer terminated the backend.

## 2. Swap Space (Optional Stopgap)
If RAM is borderline (e.g., exactly 8GB and occasionally spiking), add a swap file on the EC2 host:
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## 3. PyTorch & Python Versioning (Critical)
- **Python Version**: Standardized to `Python 3.11`.
- **PyTorch**: We explicitly use CPU-only wheels for PyTorch to avoid massive GPU dependencies and runtime crashes on non-GPU instances (e.g., `libcudart.so` missing errors).
- **Constraints**: The `constraints.txt` file strictly pins `torch`, `torchvision`, and `torchaudio` to their matching CPU builds. **DO NOT** remove this constraints file from the Docker build process, or sub-dependencies like `pyannote-audio` may overwrite them with incompatible CUDA versions.

## 4. Container & Network Configuration
- **Model Download**: The `scripts/download_models.py` runs inside the Dockerfile. Ensure your EC2 build environment has access to outbound internet and the required `HF_TOKEN` if accessing gated models.
- **Health Checks**: If behind an ELB (Elastic Load Balancer) or ALB, configure the `/health` check timeout to a minimum of `120 seconds`. Cold starts can take 30s-60s to load all ML models into memory.
- **Restart Policy**: Use `restart: always` or `restart: unless-stopped` in Docker Run or Compose so the service recovers automatically after an instance reboot.

## 5. Storage (EBS)
- The ML weights and the PyTorch CPU dependencies are large. Ensure the root EBS volume is at least **30GB**. A full disk will cause unpredictable application crashes during build or startup.
