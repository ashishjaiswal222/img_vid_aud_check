import requests
import json
import os

AUDIO_URL = "http://127.0.0.1:8000/moderation/audio-verify/check"
PHOTO_URL = "http://127.0.0.1:8000/moderation/photo-verify/check-single"

AUDIO_FILE = r"C:\Users\Ashish jaiswal\OneDrive\Desktop\projects\audiocheckAPI\sample audio to test\sampelrealaudio.m4a"
PHOTO_FILE = r"C:\Users\Ashish jaiswal\OneDrive\Desktop\projects\photo-verify-api\diff_person.jpg"
REFERENCE_PHOTO_FILE = r"C:\Users\Ashish jaiswal\OneDrive\Desktop\projects\photo-verify-api\diff_person.jpg" # Using same photo as reference just for testing the pipeline

print("="*50)
print("Testing Audio API...")
try:
    with open(AUDIO_FILE, 'rb') as f:
        files = {'file': (os.path.basename(AUDIO_FILE), f, 'audio/x-m4a')}
        data = {'session_id': 'test-session-123'}
        response = requests.post(AUDIO_URL, files=files, data=data)
        print(f"Status Code: {response.status_code}")
        print("Response:", json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Audio test failed: {e}")

print("="*50)
print("Testing Photo API...")
try:
    with open(PHOTO_FILE, 'rb') as selfie, open(REFERENCE_PHOTO_FILE, 'rb') as reference:
        files = {
            'file': (os.path.basename(PHOTO_FILE), selfie, 'image/jpeg'),
            'reference_image': (os.path.basename(REFERENCE_PHOTO_FILE), reference, 'image/jpeg')
        }
        data = {
            'session_id': 'test-session-456',
            'position': 'front'
        }
        response = requests.post(PHOTO_URL, files=files, data=data)
        print(f"Status Code: {response.status_code}")
        print("Response:", json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Photo test failed: {e}")

print("="*50)
print("Test Complete.")
