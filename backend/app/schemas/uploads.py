from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class PresignUploadRequest(BaseModel):
    org_id: uuid.UUID
    side: str = Field(pattern="^(bank|provider)$")
    original_filename: str
    content_type: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)


class PresignUploadResponse(BaseModel):
    upload_id: uuid.UUID
    storage_key: str
    presigned_url: str


class CompleteUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
