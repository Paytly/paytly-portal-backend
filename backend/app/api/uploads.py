from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import Upload
from app.db.session import get_db
from app.schemas.uploads import (
    CompleteUploadResponse,
    PresignUploadRequest,
    PresignUploadResponse,
)
from app.services.storage import build_storage_key, generate_put_presigned_url

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/presign", response_model=PresignUploadResponse, status_code=status.HTTP_201_CREATED)
def presign_upload(payload: PresignUploadRequest, db: Session = Depends(get_db)) -> PresignUploadResponse:
    storage_key = build_storage_key(payload.org_id, payload.side, payload.original_filename)
    presigned_url = generate_put_presigned_url(storage_key, payload.content_type)

    upload = Upload(
        org_id=payload.org_id,
        side=payload.side,
        status="PRESIGNED",
        storage_key=storage_key,
        original_filename=payload.original_filename,
        content_type=payload.content_type,
        size_bytes=payload.size_bytes,
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    return PresignUploadResponse(
        upload_id=upload.id,
        storage_key=upload.storage_key,
        presigned_url=presigned_url,
    )


@router.post("/{upload_id}/complete", response_model=CompleteUploadResponse)
def complete_upload(upload_id: uuid.UUID, db: Session = Depends(get_db)) -> CompleteUploadResponse:
    upload = db.get(Upload, upload_id)
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")

    upload.status = "UPLOADED"
    upload.uploaded_at = datetime.now(UTC)
    db.commit()
    db.refresh(upload)

    return CompleteUploadResponse.model_validate(upload)
