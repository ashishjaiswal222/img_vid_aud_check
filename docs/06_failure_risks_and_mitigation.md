# 6. Failure Risks & Mitigation Strategies

While the API is heavily optimized, AI inference is inherently resource-intensive. Below are the primary failure scenarios that could occur in production and how to mitigate them.

## 1. Out of Memory (OOM) Kills
**Risk Level**: High
**Symptoms**: The Docker container abruptly restarts without logging a Python stack trace. A 502 Bad Gateway is returned by the Load Balancer.
**Cause**: The server ran out of physical RAM. The Linux kernel's OOM Killer terminated the Python process to save the OS.
**Mitigation**:
- Check the EC2 host logs: `dmesg -T | grep -i "killed process"`.
- Upgrade the EC2 instance to a larger tier (e.g., `t3.xlarge`).
- Reduce `WORKER_POOL_SIZE` in your `.env` file to 1.
- Enable a Swap file on the host OS.

## 2. Broken Process Pool (Worker Crashes)
**Risk Level**: Medium
**Symptoms**: The API returns HTTP 503 with the message `"Process pool broken"`.
**Cause**: A C-level segmentation fault occurred inside one of the AI libraries (like ONNXRuntime or OpenCV), or a worker process was killed by the OS, leaving the `ProcessPoolExecutor` in a corrupted state.
**Mitigation**:
- The `/health` endpoint is configured to automatically detect `_broken` pools.
- If the pool is broken, simply restart the Docker container (`docker restart ai-api`).
- Ensure users are not uploading highly malformed or "zip-bomb" style media files that crash FFmpeg. The `max_file_size` middleware (set to 150MB) mitigates most of this.

## 3. HuggingFace Rate Limits / Model Download Failures
**Risk Level**: Low (Fixed in Dockerfile)
**Symptoms**: The application fails to start, complaining about `HTTP 401 Unauthorized` or `ConnectTimeout` when calling `huggingface.co`.
**Cause**: Pyannote models require an active `HF_TOKEN`. If the token is invalid or missing, the model cannot be downloaded.
**Mitigation**:
- The `scripts/download_models.py` script now runs *during* the Docker Build phase. This ensures that if HuggingFace is down or the token is invalid, the Docker Build will fail immediately, preventing a broken image from ever reaching production.
- Always ensure `HF_TOKEN` is passed via `--build-arg` or environment variables during CI/CD.

## 4. Unbound Disk Growth
**Risk Level**: Low
**Symptoms**: The server slowly stops responding; `df -h` shows the `/` directory at 100%.
**Cause**: When FastAPI processes `multipart/form-data` uploads, it writes them to temporary spooled files on the disk (`/tmp`). If the application crashes before cleaning these up, they can accumulate.
**Mitigation**:
- The API is designed to read files directly into memory (`await file.read()`) rather than saving them to disk where possible.
- Ensure the Docker daemon is configured to limit log sizes (e.g., `max-size: "10m"` in Docker daemon settings) so container logs don't fill the EBS volume over time.
