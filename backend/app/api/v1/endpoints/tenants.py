"""Tenant Management Endpoints (Platform Admin Only)."""
from typing import List, Union
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_platform_admin
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter()


class TenantCreate(BaseModel):
    name: str
    slug: str
    plan: str = "starter"


class TenantResponse(BaseModel):
    id: Union[uuid.UUID, str]
    name: str
    slug: str
    plan: str
    status: str

    model_config = ConfigDict(from_attributes=True)


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    payload: TenantCreate,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Tenant)
        .where(Tenant.slug == payload.slug)
        .execution_options(bypass_tenant_isolation=True)
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with slug '{payload.slug}' already exists.",
        )

    tenant = Tenant(
        name=payload.name,
        slug=payload.slug,
        plan=payload.plan,
        status="active",
    )
    db.add(tenant)
    await db.flush()
    return tenant


@router.get("", response_model=List[TenantResponse])
async def list_tenants(
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Tenant).execution_options(bypass_tenant_isolation=True)
    result = await db.execute(stmt)
    return list(result.scalars().all())
