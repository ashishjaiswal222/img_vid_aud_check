import os
from app.services.audio.utils.audio_io import load_and_normalize_audio

AUDIO_FILE = r"C:\Users\Ashish jaiswal\OneDrive\Desktop\projects\audiocheckAPI\sample audio to test\sampelrealaudio.m4a"

try:
    with open(AUDIO_FILE, 'rb') as f:
        file_bytes = f.read()
    
    audio_data, duration = load_and_normalize_audio(file_bytes, "sampelrealaudio.m4a")
    print(f"Success! Duration: {duration} seconds, Shape: {audio_data.shape}")
except Exception as e:
    print(f"Error: {e}")
