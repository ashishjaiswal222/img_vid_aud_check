import os

# Suppress annoying C++ logs from MediaPipe and ONNXRuntime
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["GLOG_minloglevel"] = "2"
os.environ["ORT_LOGGING_LEVEL"] = "3"

import structlog
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.middleware.rate_limit import RateLimitMiddleware
from app.routes.moderation import moderation_router
from app.routes.audio import router as audio_router
from app.routes.photo import router as photo_router
from app.config import settings

# Setup structlog for unified logging
logger = structlog.get_logger()

# Audio Worker Pool
from app.services.audio.workers.pool import start_worker_pool as start_audio_pool, stop_worker_pool as stop_audio_pool

# Photo Worker Pool
from app.services.photo.workers.pool import get_pool as start_photo_pool, shutdown_pool as stop_photo_pool
import numpy as np

IS_PHOTO_READY = False

async def warmup_photo_pool():
    global IS_PHOTO_READY
    logger.info("Warming up photo worker pool with dummy inference...")
    pool = start_photo_pool()
    loop = asyncio.get_running_loop()
    
    dummy_img = np.zeros((480, 480, 3), dtype=np.uint8)
    dummy_img[:, :] = (255, 0, 0)
    
    import cv2
    _, encoded = cv2.imencode('.jpg', dummy_img)
    dummy_bytes = encoded.tobytes()
    
    from app.services.photo.pipeline import verify_image
    from app.config import settings
    
    try:
        tasks = []
        for _ in range(settings.photo_worker_pool_size):
            tasks.append(loop.run_in_executor(pool, verify_image, dummy_bytes, "image/jpeg", "front"))
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logger.debug(f"Warmup inference completed with error: {e}")
        
    IS_PHOTO_READY = True
    logger.info("Photo Models are loaded. Photo Verification API is ready.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Unified API...")
    
    # 1. Start Audio Pool
    try:
        start_audio_pool()
    except Exception as e:
        logger.warning(f"Audio pool startup deferred: {e}")
    
    # 2. Start Photo Pool & Warmup
    try:
        start_photo_pool()
        asyncio.create_task(warmup_photo_pool())
    except Exception as e:
        logger.warning(f"Photo pool startup deferred: {e}")
    
    yield
    
    logger.info("Shutting down Unified API...")
    try:
        stop_audio_pool()
    except Exception:
        pass
    try:
        stop_photo_pool()
    except Exception:
        pass

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Unified Moderation & Verification API",
    description="Monolithic API handling Video Moderation, Audio Verification, and Photo Verification.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_UPLOAD_SIZE = 150 * 1024 * 1024 # 150 MB

if settings.enable_max_file_size:
    @app.middleware("http")
    async def max_file_size_middleware(request: Request, call_next):
        if request.method == "POST":
            content_length = request.headers.get("content-length")
            if content_length:
                if int(content_length) > MAX_UPLOAD_SIZE:
                    return JSONResponse(
                        status_code=413,
                        content={"error": f"Payload too large. Max size is {MAX_UPLOAD_SIZE // (1024*1024)}MB."}
                    )
        return await call_next(request)

if settings.enable_rate_limits:
    app.add_middleware(RateLimitMiddleware)

# Existing Moderation Routes (/moderation/analyze, /moderation/health)
app.include_router(moderation_router)

# Ported Audio Routes
app.include_router(audio_router, prefix="/moderation/audio-verify", tags=["Audio Verification"])

# Ported Photo Routes
app.include_router(photo_router, prefix="/moderation/photo-verify", tags=["Photo Verification"])

@app.get("/health")
def health():
    # Check if worker pools are dead/broken due to a crash
    from app.services.audio.workers.pool import get_pool as get_audio_pool
    
    photo_broken = False
    audio_broken = False
    
    try:
        photo_pool = start_photo_pool()
        if getattr(photo_pool, "_broken", False):
            photo_broken = True
    except Exception:
        pass
        
    try:
        audio_pool = get_audio_pool()
        if getattr(audio_pool, "_broken", False):
            audio_broken = True
    except Exception:
        pass
        
    if photo_broken or audio_broken:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": "Process pool broken",
                "photo_broken": photo_broken,
                "audio_broken": audio_broken
            }
        )
        
    return {"status": "ok", "photo_api_ready": IS_PHOTO_READY}