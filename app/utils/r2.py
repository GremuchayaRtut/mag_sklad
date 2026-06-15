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


def _public_url(filename: str) -> str:
    """Build a public CDN URL for the uploaded file.

    Prefers CLOUDFLARE_R2_PUBLIC_URL (https://pub-XXXX.r2.dev) when set.
    Falls back to the private API endpoint — usable only if the bucket has
    public access enabled via a custom domain or the dev URL.
    """
    base = settings.CLOUDFLARE_R2_PUBLIC_URL or settings.CLOUDFLARE_R2_ENDPOINT
    return f"{base.rstrip('/')}/{filename}"


async def upload_product_photo(file: UploadFile, business_id: uuid.UUID) -> str:
    if file.content_type not in ALLOWED_TYPES:
        raise BadRequestError(
            f"Invalid image type '{file.content_type}'. Allowed: jpeg, png, webp"
        )

    data = await file.read()

    img = Image.open(io.BytesIO(data))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=85)
    buf.seek(0)

    filename = f"products/{business_id}/{uuid.uuid4()}.webp"

    if not _r2_configured():
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
    return _public_url(filename)


async def delete_product_photo(photo_url: str) -> None:
    if not _r2_configured():
        return

    # Extract object key from either public CDN URL or private endpoint URL
    for base in filter(None, [settings.CLOUDFLARE_R2_PUBLIC_URL, settings.CLOUDFLARE_R2_ENDPOINT]):
        prefix = base.rstrip("/") + "/"
        if photo_url.startswith(prefix):
            key = photo_url[len(prefix):]
            # Strip bucket name prefix if present (private endpoint includes it)
            bucket_prefix = settings.CLOUDFLARE_R2_BUCKET + "/"
            if key.startswith(bucket_prefix):
                key = key[len(bucket_prefix):]
            try:
                _get_r2_client().delete_object(Bucket=settings.CLOUDFLARE_R2_BUCKET, Key=key)
            except Exception:
                pass  # never fail a product update because of an old photo
            return
