"""ExtractedField Model"""
import uuid
from typing import Any, List, Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, GUID, TenantMixin, TimestampMixin


class ExtractedField(Base, TenantMixin, TimestampMixin):
    __tablename__ = "extracted_fields"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("case_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    draft_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confirmed_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    applicant_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewer_decision: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    correction_history: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True, default=list)

    document: Mapped["CaseDocument"] = relationship("CaseDocument", back_populates="extracted_fields")
