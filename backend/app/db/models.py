from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Org(Base):
    """
    Keep this even without login so you can add multi-tenant later without a migration rewrite.
    For the MVP you can use a single fixed org_id.
    """
    __tablename__ = "orgs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)


class Upload(Base):
    """
    Minimal upload metadata for presigned URL flow.
    """
    __tablename__ = "uploads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False)

    # "bank" or "provider"
    side: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(Enum("PRESIGNED", "UPLOADED", name="upload_status"), nullable=False, default="PRESIGNED", server_default="PRESIGNED")

    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)

    content_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    uploaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    __table_args__ = (
        Index("idx_uploads_org_side", "org_id", "side"),
    )


class ReconciliationRun(Base):
    """
    The job entity. Keep just status + references to the two uploads.
    """
    __tablename__ = "reconciliation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False)

    status: Mapped[str] = mapped_column(String, nullable=False, default="CREATED", server_default="CREATED")

    bank_upload_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id", ondelete="SET NULL"))
    provider_upload_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id", ondelete="SET NULL"))

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    __table_args__ = (
        Index("idx_runs_org_status_created", "org_id", "status", "created_at"),
    )


class MoneyEvent(Base):
    """
    Optional for the very first MVP. Keep it if you want to show imported lines and
    build matching; otherwise you can skip this table initially.
    """
    __tablename__ = "money_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), nullable=False)

    # "bank" or "provider"
    source_side: Mapped[str] = mapped_column(String, nullable=False)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    __table_args__ = (
        Index("idx_money_events_org_run_side", "org_id", "run_id", "source_side"),
    )