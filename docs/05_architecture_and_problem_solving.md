# 5. Architecture & Problem Solving

During the development of this API, several complex architectural challenges were encountered and solved. This document outlines the rationale behind the system's current design.

## Problem 1: The PyTorch CPU vs GPU Trap
**The Problem**:
When deploying to AWS EC2 (a CPU-only instance), the application would instantly crash on startup with an error: `OSError: libcudart.so.13: cannot open shared object file`. 

**The Cause**:
Sub-dependencies like `pyannote-audio` and `speechbrain` require `torchaudio`. When running `pip install -r requirements.txt`, the standard PyPI resolver defaults to downloading the **CUDA (GPU)** versions of PyTorch. When the application started, Torchaudio attempted to load Nvidia GPU drivers (`libcudart.so`), which didn't exist on the EC2 machine.

**The Solution**:
We implemented a strict `constraints.txt` file injected into a single, unified `pip install` command in the `Dockerfile`.
```dockerfile
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -c constraints.txt \
    -r requirements.txt
```
This forces the pip resolver to prioritize the `+cpu` wheels for `torch`, `torchvision`, and `torchaudio`, guaranteeing that GPU dependencies are never pulled into the production image.

## Problem 2: FastAPI Event Loop Blocking
**The Problem**:
FastAPI is asynchronous. However, running a neural network (like Whisper or InsightFace) is purely CPU-bound synchronous math. If a user uploaded a 30-second audio file, the Whisper inference would block the Python Event Loop for 15 seconds, causing every other incoming HTTP request (even simple `/health` checks) to time out and fail.

**The Solution**:
We isolated all ML inferences into separate Python processes using `concurrent.futures.ProcessPoolExecutor`.
When a request hits FastAPI, the file payload is passed to a background worker process. The ML models live *inside* the memory of the worker process, leaving the main FastAPI event loop completely free to accept thousands of concurrent connections.

## Problem 3: Multi-processing Memory Thrashing
**The Problem**:
If 10 users uploaded photos at exactly the same time, the `ProcessPool` could attempt to spin up 10 workers simultaneously. Each worker loads a 1GB model into RAM, immediately causing the server to exceed its memory limit and crash (OOM Kill).

**The Solution**:
We capped the `WORKER_POOL_SIZE` strictly based on environment configurations. By default, the worker pool is limited to 1 or 2 processes. If 10 requests arrive, 2 are processed immediately while the other 8 are safely queued by the operating system until a worker is free. This ensures consistent, predictable memory usage at the cost of slight latency during high-traffic spikes.
