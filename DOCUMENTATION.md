# Deployment / EC2 Notes

This service runs a heavy set of ML models including Whisper (for audio transcription), SpeechBrain (for audio embeddings), PANNs (audio classification), Pyannote (diarization), MediaPipe, and NudeNet.
When deploying on EC2, please follow these guidelines:

## 1. Instance Sizing & Memory (OOM Avoidance)
- **Minimum Recommended Instance**: `t3.small` (at least 2GB RAM).
- Thanks to deep model optimizations, the AI stack consumes approximately **1.3GB RAM**.
- If using multiple worker processes (`WORKER_POOL_SIZE > 1`), RAM requirements multiply linearly. On a `t3.small`, strictly set `WORKER_POOL_SIZE=1`.
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
- **Constraints**: The `constraints.txt` file strictly pins `torch` and `torchaudio` to their matching CPU builds. **DO NOT** remove this constraints file from the Docker build process, or sub-dependencies like `pyannote-audio` may overwrite them with incompatible CUDA versions.

## 4. Container & Network Configuration
- **Model Download**: The `scripts/download_models.py` runs inside the Dockerfile. Ensure your EC2 build environment has access to outbound internet and the required `HF_TOKEN` if accessing gated models.
- **Health Checks**: If behind an ELB (Elastic Load Balancer) or ALB, configure the `/health` check timeout to a minimum of `120 seconds`. Cold starts can take 30s-60s to load all ML models into memory.
- **Restart Policy**: Use `restart: always` or `restart: unless-stopped` in Docker Run or Compose so the service recovers automatically after an instance reboot.

## 5. Storage (EBS)
- The ML weights and the PyTorch CPU dependencies are large. Ensure the root EBS volume is at least **30GB**. A full disk will cause unpredictable application crashes during build or startup.

---

## 6. Nudity Detection Tuning (`app/services/nudity.py`)

The NudeNet-based nudity detector has been tuned to significantly reduce false positives on content like gym clothes, bikinis, underwear, open hands/arms, and sports wear.

### Changes from baseline:

| Setting | Old Value | New Value | Reason |
|---|---|---|---|
| Detection confidence threshold | `0.60` | `0.50` | Calibrated across high (10 FPS) and standard FPS extractions |
| `FEMALE_BREAST_EXPOSED` label | Flagged | **Flagged with window suppression** | Bare breasts are NSFW; bikini/sports bra/deity torso handled via ±4 frame temporal window suppression |
| `BUTTOCKS_EXPOSED` label | Flagged | **Flagged with window suppression** | Bare buttocks are NSFW; swimwear handled via ±4 frame temporal window suppression |
| Covered counterpart suppression threshold | Not present | `0.25` | If `_COVERED` or context counterpart fires in current or adjacent ±4 frames, flag is suppressed |
| Min nude frames to flag video | 1 frame | **3 frames** | Single blurry/false-positive frames no longer block a video |

### Only these labels trigger NSFW:
- `FEMALE_GENITALIA_EXPOSED`
- `MALE_GENITALIA_EXPOSED`
- `ANUS_EXPOSED`
- `FEMALE_BREAST_EXPOSED` *(suppressed when `FEMALE_BREAST_COVERED`, `BELLY_EXPOSED`, `ARMPITS_EXPOSED`, or `MALE_BREAST_EXPOSED` also detected in ±4 frame window)*
- `BUTTOCKS_EXPOSED` *(suppressed when `BUTTOCKS_COVERED` also detected in ±4 frame window)*

### Tunable constants (top of `nudity.py`):
```python
DEFAULT_THRESHOLD = 0.50             # per-frame confidence minimum
COVERED_SUPPRESSION_THRESHOLD = 0.25 # covered-counterpart suppression score
NUDE_FRAME_THRESHOLD = 3             # min unsuppressed frames flagged before video = NSFW
```
