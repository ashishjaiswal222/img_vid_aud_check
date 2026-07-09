import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

# Original Video Config Variables
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET = os.getenv("S3_BUCKET")
CLOUDFRONT_URL = os.getenv("CLOUDFRONT_URL")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

class Settings(BaseSettings):
    app_name: str = "Unified Verification API"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Optional Middleware Toggles (Off by default, as Node.js Gateway handles this)
    enable_rate_limits: bool = False
    enable_max_file_size: bool = True
    
    # Audio Settings
    hf_token: str = ""
    use_overlap_heuristic_fallback: bool = False
    ffmpeg_bin_dir: str = ""
    audio_worker_pool_size: int = max(1, (os.cpu_count() or 4) // 2)
    audio_request_timeout_seconds: int = 180
    
    # Photo Settings
    photo_worker_pool_size: int = max(1, (os.cpu_count() or 4) // 2)
    photo_batch_timeout_seconds: int = 120
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()