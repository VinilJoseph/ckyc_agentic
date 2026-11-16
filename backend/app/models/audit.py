"""AuditEvent Model."""
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Index, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, GUID, TenantMixin


class AuditEvent(Base, TenantMixin):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_tenant_created", "tenant_id", "created_at"),
        Index("ix_audit_resource", "resource_type", "resource_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    # Nullable for platform/system level actions
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, nullable=True, index=True)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, nullable=True, index=True)
    actor_role: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, nullable=True)
    metadata_: Mapped[Optional[Any]] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
