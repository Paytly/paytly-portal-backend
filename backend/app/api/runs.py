from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import ReconciliationRun, Upload
from app.db.session import get_db
from app.schemas.runs import StartRunResponse

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("/{run_id}/start", response_model=StartRunResponse)
def start_run(run_id: uuid.UUID, db: Session = Depends(get_db)) -> StartRunResponse:
    run = db.get(ReconciliationRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    if not run.bank_upload_id or not run.provider_upload_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Run must have bank_upload_id and provider_upload_id",
        )

    bank_upload = db.get(Upload, run.bank_upload_id)
    provider_upload = db.get(Upload, run.provider_upload_id)

    if not bank_upload or not provider_upload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Referenced upload not found")

    if bank_upload.status != "UPLOADED" or provider_upload.status != "UPLOADED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both bank and provider uploads must be UPLOADED",
        )

    run.status = "PENDING"
    if not getattr(run, "started_at", None):
        run.started_at = datetime.now(UTC)

    db.commit()

    return StartRunResponse(run_id=run.id, status=run.status)
