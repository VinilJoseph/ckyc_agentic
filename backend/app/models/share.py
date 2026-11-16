"""ShareGrant Model."""
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, GUID, TenantMixin


class ShareGrant(Base, TenantMixin):
    __tablename__ = "share_grants"
    __table_args__ = (
        Index("ix_shares_recipient", "recipient_tenant_id", "consent_status"),
        Index("ix_shares_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    source_case_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("kyc_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requesting_tenant_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipient_tenant_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    purpose: Mapped[str] = mapped_column(String(500), nullable=False)
    selected_fields: Mapped[Any] = mapped_column(JSON, nullable=False)
    consent_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    consent_token: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    consented_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source_case: Mapped["KycCase"] = relationship("KycCase", back_populates="share_grants")
