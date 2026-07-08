# 1. Project Overview & Features

## Introduction
The **Unified AI Verification API** is a monolithic FastAPI microservice designed to perform heavy, AI-driven content moderation and identity verification. By consolidating multiple traditionally separate pipelines (Photo, Video, and Audio verification) into a single service, this project simplifies cloud deployments and creates a one-stop endpoint for KYC (Know Your Customer) and content safety checks.

## Core Features

### 1. Photo KYC Verification (`/moderation/photo-verify/check-single`)
A robust pipeline designed to process identity photos (like selfies or ID cards) to ensure they are authentic, high-quality, and structurally valid.
- **Spoofing Detection**: Analyzes the image for digital manipulation or printed photos.
- **Quality Gates**: Checks for blurriness and improper lighting (e.g., harsh shadows).
- **Face Detection & Alignment**: Accurately locates faces and verifies that the photo contains exactly one human subject.

### 2. Audio Verification (`/moderation/audio-verify/check`)
Processes raw audio to transcribe spoken words, analyze the acoustic environment, and diarize (separate) speakers.
- **Transcription**: High-fidelity speech-to-text conversion.
- **Diarization**: Determines "who spoke when" to detect overlapping voices.
- **Quality & Energy Gates**: Uses Voice Activity Detection (VAD) to ensure the audio contains actual speech, preventing the AI from hallucinating words from background noise.

### 3. Video & Image Content Moderation (`/moderation/analyze`)
Scans visual media to ensure it complies with community guidelines and safety standards.
- **NSFW Detection**: Accurately identifies explicit or inappropriate imagery.
- **Deepfake / Manipulation Checks**: Extends into validating whether a video stream has been synthetically altered.

## System Architecture

The application is built on **FastAPI** to provide high-concurrency, asynchronous routing. However, because AI inference (running neural networks) is strictly CPU-bound and blocks the Python Event Loop, the system implements a **Multiprocessing Worker Pool** pattern. 

### Why a Monolith?
Instead of orchestrating 3 separate microservices (which would require complex Docker Compose setups, inter-service networking, and 3x the baseline RAM overhead), this monolith uses isolated worker pools to distribute CPU load internally. This ensures a clean, single-container deployment on AWS EC2.
