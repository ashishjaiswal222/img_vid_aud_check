"""
Quick local test: download frames from video URLs and run
the updated nudity detection logic directly (no server needed).
"""
import sys
import os
import cv2
import requests
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.nudity import check_nudity, DEFAULT_THRESHOLD, NUDE_FRAME_THRESHOLD

VIDEO_TESTS = [
    ("Explicit Video (Taking off shirt)", "https://dvjoibo2qkfpj.cloudfront.net/swap-templates/swap-template-c297363e-9338-4792-ab9c-3cb92330bf27.mp4", True),
    ("Team Lead Video 1", "https://dvjoibo2qkfpj.cloudfront.net/swap-templates/swap-template-381961b3-7827-4747-afde-f8e9a2ed9a98.mp4", False),
    ("Team Lead Video 2", "https://dvjoibo2qkfpj.cloudfront.net/prod/videos/undefined-1778846476912.mp4", False),
    ("Team Lead Video 3 (Hanuman)", "https://d3szsaxquhat7n.cloudfront.net/prod/swap-templates/swap-template-61a69fbe-028c-4682-a9d9-0038b23c0748.mp4", False),
    ("Team Lead Video 4", "https://dvjoibo2qkfpj.cloudfront.net/swap-templates/swap-template-c56bf89c-d175-4671-8a4f-6633ba43bd6b.mp4", False),
]

FRAMES_PER_SECOND = 5


def download_video(url: str, dest: str):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, stream=True, timeout=60, headers=headers)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(1024 * 1024):
            if chunk:
                f.write(chunk)


def extract_frames(video_path: str, frame_dir: str, fps_sample: int = FRAMES_PER_SECOND):
    os.makedirs(frame_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    step = max(1, int(fps / fps_sample))

    frames = []
    count = 0
    success, image = cap.read()
    while success:
        if count % step == 0:
            fpath = os.path.join(frame_dir, f"frame_{count}.jpg")
            cv2.imwrite(fpath, image)
            frames.append(fpath)
        success, image = cap.read()
        count += 1
    cap.release()
    return frames


print("=" * 70)
print(f"  Nudity Check Real-World Test  |  threshold={DEFAULT_THRESHOLD}  |  min_frames={NUDE_FRAME_THRESHOLD}")
print("=" * 70)

all_passed = True
results_summary = []

for name, url, expected_nsfw in VIDEO_TESTS:
    print(f"\n[TEST] {name}")
    print(f"       URL: {url}")

    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "video.mp4")
        frame_dir = os.path.join(tmpdir, "frames")

        try:
            download_video(url, video_path)
            frames = extract_frames(video_path, frame_dir)
            is_nude, bad_frame = check_nudity(frames)
            
            status_str = "NSFW" if is_nude else "SAFE"
            expected_str = "NSFW" if expected_nsfw else "SAFE"
            passed = (is_nude == expected_nsfw)
            
            if not passed:
                all_passed = False

            tag = "[PASS]" if passed else "[FAIL]"
            print(f"       Verdict: {tag} Got: {status_str} (Expected: {expected_str})")
            if is_nude:
                print(f"       Violating frame: {os.path.basename(bad_frame)}")
            
            results_summary.append((tag, name, status_str, expected_str))
        except Exception as e:
            print(f"       Error: {e}")
            all_passed = False
            results_summary.append(("[ERROR]", name, "ERROR", "SAFE"))

print("\n" + "=" * 70)
print("  SUMMARY RESULTS")
print("=" * 70)
for tag, name, got, exp in results_summary:
    print(f"  {tag:<8} {name:<40} Got: {got:<6} Expected: {exp}")
print("=" * 70)
if all_passed:
    print("  ALL REAL-WORLD TESTS PASSED PERFECTLY!")
