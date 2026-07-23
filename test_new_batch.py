import sys, os, cv2, requests, tempfile, shutil
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.nudity import check_nudity, DEFAULT_THRESHOLD, NUDE_FRAME_THRESHOLD

NEW_TEST_VIDEOS = [
    # Non-nude
    ("Non-nude 1 (CloudFront)", "https://dvjoibo2qkfpj.cloudfront.net/test/videos/dynamic-video-1776334673957.mp4", False),
    ("Non-nude 2 (ourdream.ai)", "https://vid.ourdream.ai/93ffc757-f3c6-475e-99a6-485c09c1f770", False),
    
    # Nude
    ("Nude 1 (ourdream.ai)", "https://vid.ourdream.ai/945e8904-7343-45f8-9934-b1c6322cfd23", True),
    ("Nude 2 (xhpingcdn.com)", "https://thumb-v7.xhpingcdn.com/a/KrI2YFBA3HQcSdxelOYTgw/014/820/027/526x298.94.3.5.t.av1.mp4", True),
    ("Nude 3 (ourdream cdn-cgi 5d2d)", "https://vid.ourdream.ai/cdn-cgi/media/mode=video,width=720,audio=false/https://vid.ourdream.ai/5d2d9c89-a056-4956-94d9-ab54c3aa243d", True),
    ("Nude 4 (ourdream cdn-cgi 4433)", "https://vid.ourdream.ai/cdn-cgi/media/mode=video,width=720,audio=false/https://vid.ourdream.ai/44335fd8-81d9-495b-bc62-984a8150a0cf", True),
]

def download_file(url, dest):
    # Strip anchor fragments if present
    clean_url = url.split('#')[0]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    r = requests.get(clean_url, stream=True, timeout=60, headers=headers)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(1024 * 1024):
            if chunk:
                f.write(chunk)

def extract_frames(video_path, frame_dir, sample_fps=5):
    os.makedirs(frame_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    step = max(1, int(fps / sample_fps))
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

print("=" * 80)
print(f"TESTING NEW REAL-WORLD VIDEOS (threshold={DEFAULT_THRESHOLD}, min_frames={NUDE_FRAME_THRESHOLD})")
print("=" * 80)

results_list = []

for name, url, expected_nsfw in NEW_TEST_VIDEOS:
    print(f"\n[TESTING] {name}")
    print(f"          URL: {url}")
    tmpdir = tempfile.mkdtemp()
    vpath = os.path.join(tmpdir, "v.mp4")
    fdir = os.path.join(tmpdir, "frames")
    
    try:
        download_file(url, vpath)
        size_mb = os.path.getsize(vpath) / (1024 * 1024)
        frames = extract_frames(vpath, fdir, sample_fps=5)
        print(f"          Downloaded ({size_mb:.1f} MB), Extracted {len(frames)} frames")
        
        is_nude, bad_frame = check_nudity(frames)
        got_nsfw = is_nude
        
        passed = (got_nsfw == expected_nsfw)
        tag = "[PASS]" if passed else "[FAIL]"
        got_str = "NSFW" if got_nsfw else "SAFE"
        exp_str = "NSFW" if expected_nsfw else "SAFE"
        
        print(f"          Verdict: {tag} Got: {got_str} (Expected: {exp_str})")
        if bad_frame:
            print(f"          Flagged Frame: {os.path.basename(bad_frame)}")
            
        results_list.append((tag, name, got_str, exp_str))
    except Exception as e:
        print(f"          ERROR: {e}")
        results_list.append(("[ERROR]", name, str(e), "EXPECTED"))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

print("\n" + "=" * 80)
print("  SUMMARY OF RESULTS")
print("=" * 80)
for tag, name, got, exp in results_list:
    print(f"  {tag:<8} {name:<35} Got: {got:<6} Expected: {exp}")
print("=" * 80)
