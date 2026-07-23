# app/services/nudity.py
from nudenet import NudeDetector

_detector = None

def _get_detector():
    global _detector
    if _detector is None:
        from nudenet import NudeDetector
        _detector = NudeDetector()
    return _detector


# ─────────────────────────────────────────────────────────────────────────────
# STRICTLY NSFW: only truly explicit / genitalia exposure counts as nudity.
# Bikinis, underwear, gym wear, open hands, and similar are NOT flagged.
#
# NOT included (intentionally):
#   - FEMALE_BREAST_EXPOSED   → covers bikini tops / sports bras false-positives
#   - BUTTOCKS_EXPOSED        → covers swimwear / gym shorts false-positives
#   - MALE_BREAST_EXPOSED     → normal (shirtless men are not nudity)
#   - BELLY_EXPOSED           → crop-tops, gym wear
#   - ARMPITS_EXPOSED         → sleeveless clothes, open hands
# ─────────────────────────────────────────────────────────────────────────────
NUDE_LABELS = {
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "ANUS_EXPOSED",
}

# If a "covered" counterpart is detected with high confidence alongside an
# "exposed" label, we treat it as a false-positive (e.g. bikini bottom
# sometimes fires both FEMALE_GENITALIA_EXPOSED and FEMALE_GENITALIA_COVERED).
COVERED_COUNTERPARTS = {
    "FEMALE_GENITALIA_EXPOSED": "FEMALE_GENITALIA_COVERED",
    "ANUS_EXPOSED":             "ANUS_COVERED",
    "BUTTOCKS_EXPOSED":         "BUTTOCKS_COVERED",
    "FEMALE_BREAST_EXPOSED":    "FEMALE_BREAST_COVERED",
}

# Higher threshold = fewer false positives.
# 0.75 is a good balance: catches real nudity, ignores gym/sports wear.
DEFAULT_THRESHOLD = 0.75

# If a covered-counterpart is detected above this score we suppress the flag.
COVERED_SUPPRESSION_THRESHOLD = 0.55

# Minimum number of video frames that must be flagged as nude before the
# entire video is marked NSFW.  A single bad frame (motion blur, false
# positive) is ignored; only a sustained pattern triggers a block.
NUDE_FRAME_THRESHOLD = 5


def _is_suppressed_by_covered(label: str, results: list, covered_threshold: float) -> bool:
    """Return True if a covered counterpart is detected with enough confidence."""
    covered_label = COVERED_COUNTERPARTS.get(label)
    if not covered_label:
        return False
    for r in results:
        if r.get("class") == covered_label and r.get("score", 0) >= covered_threshold:
            return True
    return False


def _has_nudity(results: list, threshold: float = DEFAULT_THRESHOLD) -> bool:
    """
    Core logic: returns True only when a genuinely explicit label is detected
    above the threshold AND is NOT suppressed by a covered-counterpart detection.
    """
    for r in results:
        label = r.get("class")
        score = r.get("score", 0)
        if label in NUDE_LABELS and score >= threshold:
            if not _is_suppressed_by_covered(label, results, COVERED_SUPPRESSION_THRESHOLD):
                return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO (frames)
# -----------------------------------------------------------------------------
def check_nudity(frames, threshold=DEFAULT_THRESHOLD, nude_frame_threshold=NUDE_FRAME_THRESHOLD):
    """
    Scan extracted video frames for nudity.

    A video is only marked NSFW when at least `nude_frame_threshold` frames
    are independently detected as nude (default = 5).  This prevents a single
    blurry / falsely-detected frame from blocking an otherwise clean video.

    Returns:
        (True,  first_violating_frame_path)  if nude frame count >= threshold
        (False, None)                         otherwise
    """
    nude_frames = []

    for frame in frames:
        results = _get_detector().detect(frame)
        if _has_nudity(results, threshold):
            nude_frames.append(frame)
            # Early exit once we have enough evidence — no need to scan further
            if len(nude_frames) >= nude_frame_threshold:
                return True, nude_frames[0]  # return first violating frame

    # Not enough nude frames — treat as safe
    return False, None


# ─────────────────────────────────────────────────────────────────────────────
# 🖼 IMAGE (single file)
# ─────────────────────────────────────────────────────────────────────────────
def check_image_nudity(image_path, threshold=DEFAULT_THRESHOLD):
    """
    Check a single image for nudity.
    Returns (True, image_path) or (False, None).
    """
    results = _get_detector().detect(image_path)
    if _has_nudity(results, threshold):
        return True, image_path

    return False, None