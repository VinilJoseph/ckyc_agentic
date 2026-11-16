"""MailIngestionRecord Model."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, GUID, TenantMixin

if TYPE_CHECKING:
    from app.models.case import KycCase


class MailIngestionRecord(Base, TenantMixin):
    __tablename__ = "mail_ingestion_records"
    __table_args__ = (
        Index("ix_mail_tenant_status", "tenant_id", "status"),
        Index("ix_mail_message_id", "message_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    # Nullable for unmatched inbound emails routed to platform exception queue
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, nullable=True, index=True)
    message_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    sender: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient: Mapped[str] = mapped_column(
        String(255), nullable=False, default="kyc-intake@fintechbank.com"
    )
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="received")
    case_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID, ForeignKey("kyc_cases.id", ondelete="SET NULL"), nullable=True, index=True
    )
    attachment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_payload_storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    case: Mapped[Optional["KycCase"]] = relationship("KycCase", foreign_keys=[case_id])
