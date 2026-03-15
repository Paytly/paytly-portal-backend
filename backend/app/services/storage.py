from __future__ import annotations

import uuid
import boto3

from app.core.config import settings


s3_client = boto3.client("s3", region_name=settings.aws_region) # pyright: ignore[reportUnknownMemberType]

def build_storage_key(org_id: uuid.UUID, side: str, filename: str) -> str:
    safe_name = filename.replace(" ", "_")
    return f"uploads/{org_id}/{side}/{uuid.uuid4()}-{safe_name}"


def generate_put_presigned_url(storage_key: str, content_type: str | None = None) -> str:
    params = {
        "Bucket": settings.s3_bucket_name,
        "Key": storage_key,
    }
    if content_type:
        params["ContentType"] = content_type

    return s3_client.generate_presigned_url(
        ClientMethod="put_object",
        Params=params,
        ExpiresIn=settings.s3_presign_expires_seconds,
        HttpMethod="PUT",
    )
