from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    s3_bucket_name: str
    aws_region: str = "sa-east-1"
    s3_presign_expires_seconds: int = 900


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


settings = Settings(
    database_url=_required_env("DATABASE_URL"),
    s3_bucket_name=_required_env("S3_BUCKET_NAME"),
    aws_region=os.getenv("AWS_REGION", "sa-east-1"),
    s3_presign_expires_seconds=int(os.getenv("S3_PRESIGN_EXPIRES_SECONDS", "900")),
)
