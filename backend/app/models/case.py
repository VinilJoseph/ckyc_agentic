"""KycCase Model with Biometric & Validation State Persistence."""
import uuid
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, GUID, TenantMixin, TimestampMixin


class KycCase(Base, TenantMixin, TimestampMixin):
    __tablename__ = "kyc_cases"
    __table_args__ = (
        Index("ix_cases_tenant_status", "tenant_id", "status"),
        Index("ix_cases_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("applicants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(500), nullable=False)
    case_type: Mapped[str] = mapped_column(String(20), nullable=False)  # individual | business
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    review_decision: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    review_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def reason(self) -> Optional[str]:
        return self.review_reason

    # Milestone 2: Persisted Biometric and Validation state
    selfie_match: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    validation_issues: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True, default=list)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="cases")
    applicant: Mapped["Applicant"] = relationship("Applicant", back_populates="cases")
    reviewer: Mapped[Optional["User"]] = relationship("User")
    documents: Mapped[List["CaseDocument"]] = relationship(
        "CaseDocument", back_populates="case", cascade="all, delete-orphan"
    )
    share_grants: Mapped[List["ShareGrant"]] = relationship(
        "ShareGrant", back_populates="source_case", cascade="all, delete-orphan"
    )
