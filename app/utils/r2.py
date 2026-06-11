import io
import uuid

import boto3
from fastapi import UploadFile
from PIL import Image

from app.config import settings
from app.core.exceptions import BadRequestError

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_DIMENSION = 400


def _get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.CLOUDFLARE_R2_ENDPOINT,
        aws_access_key_id=settings.CLOUDFLARE_R2_ACCESS_KEY,
        aws_secret_access_key=settings.CLOUDFLARE_R2_SECRET_KEY,
        region_name="auto",
    )


def _r2_configured() -> bool:
    return bool(settings.CLOUDFLARE_R2_ACCESS_KEY and settings.CLOUDFLARE_R2_BUCKET)


async def upload_product_photo(file: UploadFile, business_id: uuid.UUID) -> str:
    if file.content_type not in ALLOWED_TYPES:
        raise BadRequestError(
            f"Invalid image type '{file.content_type}'. Allowed: jpeg, png, webp"
        )

    data = await file.read()

    img = Image.open(io.BytesIO(data))
    # Convert RGBA / P modes so WebP encoder is happy
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=85)
    buf.seek(0)

    filename = f"products/{business_id}/{uuid.uuid4()}.webp"

    if not _r2_configured():
        # Local fallback for development
        local_path = f"/tmp/{filename.replace('/', '_')}"
        with open(local_path, "wb") as f:
            f.write(buf.read())
        return local_path

    client = _get_r2_client()
    client.upload_fileobj(
        buf,
        settings.CLOUDFLARE_R2_BUCKET,
        filename,
        ExtraArgs={"ContentType": "image/webp"},
    )
    return f"{settings.CLOUDFLARE_R2_ENDPOINT}/{settings.CLOUDFLARE_R2_BUCKET}/{filename}"


async def delete_product_photo(photo_url: str) -> None:
    if not _r2_configured():
        return

    prefix = f"{settings.CLOUDFLARE_R2_ENDPOINT}/{settings.CLOUDFLARE_R2_BUCKET}/"
    if not photo_url.startswith(prefix):
        return

    key = photo_url[len(prefix):]
    try:
        _get_r2_client().delete_object(Bucket=settings.CLOUDFLARE_R2_BUCKET, Key=key)
    except Exception:
        pass  # never fail a product update because of an old photo
