"""
ISO 27001 A.12.4.1 — Event logging.
Persisted audit trail — every security-relevant action is recorded.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    ts: Mapped[datetime]  = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    event: Mapped[str]    = mapped_column(String(64), nullable=False, index=True)
    subject: Mapped[str | None] = mapped_column(String(254), nullable=True)
    ip: Mapped[str | None]      = mapped_column(String(45), nullable=True)
    detail: Mapped[str | None]  = mapped_column(Text, nullable=True)
