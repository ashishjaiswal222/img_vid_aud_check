# app/services/nudity.py
from nudenet import NudeDetector

_detector = None

def _get_detector():
    global _detector
    if _detector is None:
        from nudenet import NudeDetector
        _detector = NudeDetector()
    return _detector
NUDE_LABELS = {
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "ANUS_EXPOSED",
    "FEMALE_BREAST_EXPOSED",
    "BUTTOCKS_EXPOSED"
}


# 🎥 VIDEO (frames)
def check_nudity(frames, threshold=0.6):
    for frame in frames:
        results = _get_detector().detect(frame)

        for r in results:
            if r.get("class") in NUDE_LABELS and r.get("score", 0) >= threshold:
                return True, frame  # return violating frame

    return False, None


# 🖼 IMAGE (single file)
def check_image_nudity(image_path, threshold=0.6):
    results = _get_detector().detect(image_path)

    for r in results:
        if r.get("class") in NUDE_LABELS and r.get("score", 0) >= threshold:
            return True, image_path  # return same image

    return False, None