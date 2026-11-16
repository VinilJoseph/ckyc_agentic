"""Applicant and BusinessRepresentative Models (Single-Table Polymorphism)."""
import uuid
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, GUID, TenantMixin


class Applicant(Base, TenantMixin):
    __tablename__ = "applicants"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    applicant_type: Mapped[str] = mapped_column(String(20), nullable=False)  # person | business
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Person-specific
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    nationality: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Business-specific
    business_name: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    registration_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    incorporation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    cases: Mapped[List["KycCase"]] = relationship(
        "KycCase", back_populates="applicant", cascade="all, delete-orphan"
    )
    representatives: Mapped[List["BusinessRepresentative"]] = relationship(
        "BusinessRepresentative", back_populates="business", cascade="all, delete-orphan"
    )


class BusinessRepresentative(Base, TenantMixin):
    __tablename__ = "business_representatives"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("applicants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role_title: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False, default="unverified")

    business: Mapped["Applicant"] = relationship("Applicant", back_populates="representatives")
