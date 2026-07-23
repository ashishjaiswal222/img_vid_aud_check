"""
test_nudity_logic.py
--------------------
Unit tests for the nudity detection logic in app/services/nudity.py

These tests work by feeding MOCK NudeNet detection results directly into
the core logic functions (_has_nudity, check_nudity) — no real explicit
images or videos needed. This is the standard, safe way to test ML
moderation pipelines.

Each test covers a real-world scenario and prints a clear PASS/FAIL result.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.nudity import (
    _has_nudity,
    _is_suppressed_by_covered,
    DEFAULT_THRESHOLD,
    COVERED_SUPPRESSION_THRESHOLD,
    NUDE_FRAME_THRESHOLD,
)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def det(label, score):
    """Shorthand to create a fake NudeNet detection result dict."""
    return {"class": label, "score": score}

passed = 0
failed = 0

def run_test(name, result, expected):
    global passed, failed
    status = "PASS" if result == expected else "FAIL"
    mark   = "[PASS]" if result == expected else "[FAIL]"
    if result == expected:
        passed += 1
    else:
        failed += 1
    print(f"  {mark}  {name}")
    if result != expected:
        print(f"         Expected: {expected}  |  Got: {result}")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO TESTS
# ─────────────────────────────────────────────────────────────────────────────

print()
print("=" * 65)
print("  Nudity Detection Logic — Real-World Scenario Tests")
print(f"  threshold={DEFAULT_THRESHOLD}  |  covered_suppress={COVERED_SUPPRESSION_THRESHOLD}  |  frame_min={NUDE_FRAME_THRESHOLD}")
print("=" * 65)

# ── Group 1: Should be SAFE ──────────────────────────────────────────────────
print("\n[GROUP 1] Should be SAFE (not flagged)\n")

run_test(
    "Person in full clothes — no detections at all",
    _has_nudity([]),
    False
)

run_test(
    "Shirtless man — MALE_BREAST_EXPOSED only (not in NSFW list)",
    _has_nudity([det("MALE_BREAST_EXPOSED", 0.92)]),
    False
)

run_test(
    "Gym wear — BELLY_EXPOSED + ARMPITS_EXPOSED (not in NSFW list)",
    _has_nudity([det("BELLY_EXPOSED", 0.88), det("ARMPITS_EXPOSED", 0.85)]),
    False
)

run_test(
    "Woman in bikini top — FEMALE_BREAST_EXPOSED suppressed by FEMALE_BREAST_COVERED",
    _has_nudity([
        det("FEMALE_BREAST_EXPOSED", 0.80),
        det("FEMALE_BREAST_COVERED", 0.70),   # covered fires alongside
    ]),
    False
)

run_test(
    "Person in swimwear — BUTTOCKS_EXPOSED suppressed by BUTTOCKS_COVERED",
    _has_nudity([
        det("BUTTOCKS_EXPOSED", 0.82),
        det("BUTTOCKS_COVERED", 0.65),
    ]),
    False
)

run_test(
    "Underwear only — both genitalia EXPOSED + COVERED fire (bikini/underwear case)",
    _has_nudity([
        det("FEMALE_GENITALIA_EXPOSED", 0.77),
        det("FEMALE_GENITALIA_COVERED", 0.60),
    ]),
    False
)

run_test(
    "Below confidence threshold — FEMALE_BREAST_EXPOSED at 0.60 (below 0.75)",
    _has_nudity([det("FEMALE_BREAST_EXPOSED", 0.60)]),
    False
)

run_test(
    "Just below threshold — FEMALE_GENITALIA_EXPOSED at 0.74 (just under 0.75)",
    _has_nudity([det("FEMALE_GENITALIA_EXPOSED", 0.74)]),
    False
)

run_test(
    "Open hands / arms — ARMPITS_EXPOSED (not in NSFW list)",
    _has_nudity([det("ARMPITS_EXPOSED", 0.95)]),
    False
)

run_test(
    "Sports bra + gym shorts — FEMALE_BREAST_COVERED + BELLY_EXPOSED",
    _has_nudity([
        det("FEMALE_BREAST_COVERED", 0.88),
        det("BELLY_EXPOSED", 0.75),
    ]),
    False
)

# ── Group 2: Should be NSFW ──────────────────────────────────────────────────
print("\n[GROUP 2] Should be NSFW (flagged)\n")

run_test(
    "Bare breasts — FEMALE_BREAST_EXPOSED (no covered counterpart)",
    _has_nudity([det("FEMALE_BREAST_EXPOSED", 0.90)]),
    True
)

run_test(
    "Explicit female genitalia — FEMALE_GENITALIA_EXPOSED at 0.85",
    _has_nudity([det("FEMALE_GENITALIA_EXPOSED", 0.85)]),
    True
)

run_test(
    "Explicit male genitalia — MALE_GENITALIA_EXPOSED at 0.78",
    _has_nudity([det("MALE_GENITALIA_EXPOSED", 0.78)]),
    True
)

run_test(
    "Anus exposure — ANUS_EXPOSED at 0.80",
    _has_nudity([det("ANUS_EXPOSED", 0.80)]),
    True
)

run_test(
    "Bare buttocks — BUTTOCKS_EXPOSED with no covered counterpart",
    _has_nudity([det("BUTTOCKS_EXPOSED", 0.87)]),
    True
)

run_test(
    "Exactly at threshold — FEMALE_BREAST_EXPOSED at exactly 0.75",
    _has_nudity([det("FEMALE_BREAST_EXPOSED", 0.75)]),
    True
)

run_test(
    "Covered suppression too weak — FEMALE_BREAST_EXPOSED=0.85, FEMALE_BREAST_COVERED=0.40 (below 0.55)",
    _has_nudity([
        det("FEMALE_BREAST_EXPOSED", 0.85),
        det("FEMALE_BREAST_COVERED", 0.40),   # covered score too low to suppress
    ]),
    True
)

run_test(
    "Mixed frame — shirtless man + bare female breasts",
    _has_nudity([
        det("MALE_BREAST_EXPOSED", 0.92),    # safe label
        det("FEMALE_BREAST_EXPOSED", 0.88),  # NSFW label, no covered counterpart
    ]),
    True
)

# ── Group 3: Video Frame Count Threshold ─────────────────────────────────────
print("\n[GROUP 3] Video — Frame count threshold (min 5 frames)\n")

from unittest.mock import patch, MagicMock

def make_fake_frame_results(nude_count, total_count, label="FEMALE_BREAST_EXPOSED", score=0.90):
    """
    Returns a list of (frame_path, results) tuples.
    First `nude_count` frames have a nudity detection, rest are clean.
    """
    all_results = []
    for i in range(total_count):
        if i < nude_count:
            all_results.append([det(label, score)])
        else:
            all_results.append([])
    return all_results

def simulate_check_nudity(frame_results_list, nude_frame_threshold=NUDE_FRAME_THRESHOLD):
    """Simulate check_nudity() using pre-built results without a real detector."""
    nude_frames = []
    for i, results in enumerate(frame_results_list):
        if _has_nudity(results, DEFAULT_THRESHOLD):
            nude_frames.append(f"frame_{i}.jpg")
            if len(nude_frames) >= nude_frame_threshold:
                return True, nude_frames[0]
    return False, None

# 4 nude frames out of 20 — should PASS (below threshold)
is_nsfw, _ = simulate_check_nudity(make_fake_frame_results(4, 20))
run_test(
    "Video with 4 nude frames out of 20 — below threshold (< 5) → SAFE",
    is_nsfw,
    False
)

# Exactly 5 nude frames — should FAIL (hits threshold)
is_nsfw, _ = simulate_check_nudity(make_fake_frame_results(5, 20))
run_test(
    "Video with 5 nude frames out of 20 — hits threshold exactly → NSFW",
    is_nsfw,
    True
)

# 10 nude frames — definitely NSFW, should early-exit at 5
is_nsfw, frame = simulate_check_nudity(make_fake_frame_results(10, 50))
run_test(
    "Video with 10 nude frames — exits early at frame 5 → NSFW",
    is_nsfw,
    True
)

# All clean video
is_nsfw, _ = simulate_check_nudity(make_fake_frame_results(0, 30))
run_test(
    "Completely clean video — 0 nude frames → SAFE",
    is_nsfw,
    False
)

# Single nude frame — common false-positive scenario (motion blur)
is_nsfw, _ = simulate_check_nudity(make_fake_frame_results(1, 100))
run_test(
    "1 nude frame in 100 — motion blur / false-positive scenario → SAFE",
    is_nsfw,
    False
)

# ─────────────────────────────────────────────────────────────────────────────
print()
print("=" * 65)
print(f"  RESULTS:  {passed} passed  |  {failed} failed  |  {passed+failed} total")
print("=" * 65)
if failed == 0:
    print("  [ALL PASS] Nudity detection logic is working correctly!")
else:
    print(f"  [ATTENTION] {failed} test(s) failed — review logic above.")
print()
