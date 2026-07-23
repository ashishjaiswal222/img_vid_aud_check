import boto3
import uuid
from app.config import (
    AWS_REGION,
    S3_BUCKET,
    CLOUDFRONT_URL,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY
)

# ✅ create client (supports both env + IAM role)
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
    s3 = boto3.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
else:
    s3 = boto3.client("s3", region_name=AWS_REGION)


def upload_frame(file_path):
    try:
        key = f"nudity-frames/{uuid.uuid4()}.jpg"
        s3.upload_file(
            file_path,
            S3_BUCKET,
            key,
            ExtraArgs={"ContentType": "image/jpeg"}
        )
        return f"{CLOUDFRONT_URL}/{key}"
    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        logger.warning("S3 upload skipped or unconfigured", error=str(e))
        return file_path