"""SQLAlchemy 2.0 Async SQLite Engine & 3-Tier Multi-Tenancy Protection."""
from typing import AsyncGenerator, Optional, Type, TypeVar
import uuid

from fastapi import HTTPException, status
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, with_loader_criteria

from app.core.config import settings
from app.core.context import (
    CrossTenantAccessException,
    TenantContextMissingError,
    get_current_tenant_id_optional,
)
from app.models.base import Base, TenantMixin

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

T = TypeVar("T")


# Tier 1 Multi-Tenancy: Dynamic with_loader_criteria injection
@event.listens_for(Session, "do_orm_execute")
def receive_do_orm_execute(orm_execute_state):
    if orm_execute_state.is_select:
        tenant_id = get_current_tenant_id_optional()
        if tenant_id and not orm_execute_state.execution_options.get("bypass_tenant_isolation", False):
            orm_execute_state.statement = orm_execute_state.statement.options(
                with_loader_criteria(
                    TenantMixin,
                    lambda cls: cls.tenant_id == tenant_id,
                    include_run_time_objects=True,
                )
            )


# Tier 2 Multi-Tenancy: Guarding insertions, updates, and DELETIONS
@event.listens_for(Session, "before_flush")
def validate_tenant_flush(session, flush_context, instances):
    tenant_id = get_current_tenant_id_optional()
    if not tenant_id:
        return

    # Check all new, modified, and deleted instances
    for instance in session.new.union(session.dirty).union(session.deleted):
        if isinstance(instance, TenantMixin):
            # Allow platform records with explicitly null tenant_id
            if instance.tenant_id is not None and instance.tenant_id != tenant_id:
                raise CrossTenantAccessException(
                    f"Cross-tenant operation prevented on {instance.__class__.__name__}: "
                    f"ambient={tenant_id}, row={instance.tenant_id}"
                )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Tier 3 Multi-Tenancy: Explicit get_scoped_or_404
async def get_scoped_or_404(
    db: AsyncSession,
    model: Type[T],
    id: uuid.UUID,
    tenant_id: Optional[uuid.UUID] = None,
) -> T:
    stmt = select(model).where(model.id == id)
    if tenant_id and issubclass(model, TenantMixin):
        stmt = stmt.where(model.tenant_id == tenant_id)

    result = await db.execute(stmt)
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model.__name__} not found",
        )
    return obj
