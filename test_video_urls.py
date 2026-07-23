"""
Quick local test: download a few frames from each video URL and run
the updated nudity detection logic directly (no server needed).
"""
import sys
import os
import cv2
import requests
import tempfile
import json

# Fix Windows console encoding
sys.stdout.reconfigure(encoding="utf-8")

# Add the project root to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.nudity import check_nudity, DEFAULT_THRESHOLD

VIDEO_URLS = [
    "https://dvjoibo2qkfpj.cloudfront.net/swap-templates/swap-template-381961b3-7827-4747-afde-f8e9a2ed9a98.mp4",
    "https://dvjoibo2qkfpj.cloudfront.net/prod/videos/undefined-1778846476912.mp4",
    "https://d3szsaxquhat7n.cloudfront.net/prod/swap-templates/swap-template-61a69fbe-028c-4682-a9d9-0038b23c0748.mp4",
    "https://dvjoibo2qkfpj.cloudfront.net/swap-templates/swap-template-c56bf89c-d175-4671-8a4f-6633ba43bd6b.mp4",
]

FRAMES_TO_SAMPLE = 5   # how many frames to extract per video for quick test


def download_video(url: str, dest: str):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, stream=True, timeout=60, headers=headers)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(1024 * 1024):
            if chunk:
                f.write(chunk)


def extract_sample_frames(video_path: str, frame_dir: str, n: int = FRAMES_TO_SAMPLE):
    """Extract n evenly-spaced frames from the video."""
    os.makedirs(frame_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    step = max(1, total // n)

    frames = []
    count = 0
    idx = 0
    success, image = cap.read()
    while success:
        if count % step == 0 and idx < n:
            fpath = os.path.join(frame_dir, f"frame_{count}.jpg")
            cv2.imwrite(fpath, image)
            frames.append(fpath)
            idx += 1
        success, image = cap.read()
        count += 1
    cap.release()
    return frames


results_summary = []

print("=" * 65)
print(f"  Nudity Check Test  |  threshold = {DEFAULT_THRESHOLD}")
print("=" * 65)

for i, url in enumerate(VIDEO_URLS, 1):
    short = url.split("/")[-1][:55]
    print(f"\n[{i}] {short}")
    print(f"    URL: {url}")

    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "video.mp4")
        frame_dir  = os.path.join(tmpdir, "frames")

        # Download
        try:
            print("    [DL]  Downloading...", end=" ", flush=True)
            download_video(url, video_path)
            size_mb = os.path.getsize(video_path) / (1024 * 1024)
            print(f"OK ({size_mb:.1f} MB)")
        except Exception as e:
            print(f"FAILED — {e}")
            results_summary.append({"url": url, "result": "DOWNLOAD_ERROR", "error": str(e)})
            continue

        # Extract frames
        try:
            print(f"    [FR]  Extracting {FRAMES_TO_SAMPLE} sample frames...", end=" ", flush=True)
            frames = extract_sample_frames(video_path, frame_dir)
            print(f"OK ({len(frames)} frames)")
        except Exception as e:
            print(f"FAILED — {e}")
            results_summary.append({"url": url, "result": "FRAME_ERROR", "error": str(e)})
            continue

        # Run nudity check
        try:
            print("    [ND]  Running nudity detection...", end=" ", flush=True)
            is_nude, bad_frame = check_nudity(frames)
            verdict = "[FAIL] NSFW (FLAGGED)" if is_nude else "[PASS] SAFE"
            print(verdict)
            if is_nude:
                print(f"    [!!] Violating frame: {bad_frame}")
            results_summary.append({
                "url": url,
                "result": "NSFW" if is_nude else "SAFE",
                "frames_checked": len(frames),
            })
        except Exception as e:
            print(f"FAILED — {e}")
            results_summary.append({"url": url, "result": "DETECTION_ERROR", "error": str(e)})

print("\n" + "=" * 65)
print("  SUMMARY")
print("=" * 65)
for r in results_summary:
    status = r["result"]
    icon = "[PASS]" if status == "SAFE" else ("[FAIL]" if status == "NSFW" else "[ERR] ")
    short_url = r["url"].split("/")[-1][:50]
    print(f"  {icon}  {status:<18}  {short_url}")

print("=" * 65)
