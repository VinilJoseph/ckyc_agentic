"""Tenant, Subscription, and UsageRecord Models."""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import CHAR, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, GUID, TenantMixin


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    plan: Mapped[str] = mapped_column(String(30), nullable=False, default="starter")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    memberships: Mapped[List["TenantMembership"]] = relationship(
        "TenantMembership", back_populates="tenant", cascade="all, delete-orphan"
    )
    cases: Mapped[List["KycCase"]] = relationship(
        "KycCase", back_populates="tenant", cascade="all, delete-orphan"
    )
    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription", back_populates="tenant", cascade="all, delete-orphan"
    )
    usage_records: Mapped[List["UsageRecord"]] = relationship(
        "UsageRecord", back_populates="tenant", cascade="all, delete-orphan"
    )


class Subscription(Base, TenantMixin):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    plan: Mapped[str] = mapped_column(String(30), nullable=False)
    monthly_case_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="subscriptions")


class UsageRecord(Base, TenantMixin):
    __tablename__ = "usage_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "metric_name", name="uq_tenant_metric"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    metric_name: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="usage_records")


# Re-export TenantMembership for compatibility
from app.models.user import TenantMembership  # noqa: F401, E402
