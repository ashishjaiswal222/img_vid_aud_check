import sys
import json
import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

BASE_DIR = r"C:\Users\Ashish jaiswal\OneDrive\Desktop\projects\photo-verify-api\tests\sampleimage"
IMAGES_TO_TEST = [
    "front.png", 
    "singlefrontfacewithsunglasses.png",
    "beautiful-cartoon-woman-portrait.jpg",
    "left.png"
]

results_out = {}

for img_name in IMAGES_TO_TEST:
    img_path = os.path.join(BASE_DIR, img_name)
    if not os.path.exists(img_path):
        continue
        
    try:
        with open(img_path, "rb") as f:
            files = {"file": (img_name, f, "image/jpeg")}
            data = {"position": "front"}
            res = client.post("/moderation/photo-verify/check-single", files=files, data=data)
            
            if res.status_code == 200:
                results_out[img_name] = res.json()
            else:
                results_out[img_name] = {"error": res.text}
    except Exception as e:
        results_out[img_name] = {"error": str(e)}

with open("test_results.json", "w", encoding="utf-8") as f:
    json.dump(results_out, f, indent=2)
