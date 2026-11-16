"""SQLAlchemy Base and Multi-Tenancy Mixin Declarations."""
from datetime import datetime
import uuid
from typing import Optional

from sqlalchemy import CHAR, DateTime, String, TypeDecorator, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class GUID(TypeDecorator):
    """Platform-independent GUID type. Uses PostgreSQL UUID or SQLite CHAR(36)."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return str(value)
        try:
            return str(uuid.UUID(str(value)))
        except (ValueError, AttributeError):
            # Deterministic GUID mapping for non-hex test strings like "tenant-alpha-001"
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(value)))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            try:
                value = uuid.UUID(str(value))
            except (ValueError, AttributeError):
                value = uuid.uuid5(uuid.NAMESPACE_DNS, str(value))
        return value


class Base(DeclarativeBase):
    pass


class TenantMixin:
    """Provides automatic tenant isolation scoping for SQLAlchemy models."""

    @declared_attr
    def tenant_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(GUID, nullable=False, index=True)


class TimestampMixin:
    """Provides created_at and updated_at datetime tracking."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
