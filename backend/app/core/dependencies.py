"""FastAPI Authentication & Tenant Context Dependencies."""
from typing import Optional
import uuid

from fastapi import Depends, Header, HTTPException, Request, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.context import set_current_tenant_id
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import TenantMembership, User


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        # Check Authorization header bearer token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
        )

    try:
        payload = decode_access_token(token)
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            user_id = uuid.uuid5(uuid.NAMESPACE_DNS, str(user_id_str))
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    stmt = (
        select(User)
        .options(selectinload(User.memberships))
        .where(User.id == user_id)
        .execution_options(bypass_tenant_isolation=True)
    )
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")

    token_tenant_id_str = payload.get("tenant_id")
    if token_tenant_id_str:
        try:
            token_tenant_id = uuid.UUID(token_tenant_id_str)
        except ValueError:
            token_tenant_id = uuid.uuid5(uuid.NAMESPACE_DNS, str(token_tenant_id_str))
    else:
        token_tenant_id = None

    # Sync active role from database membership
    if token_tenant_id:
        membership = next(
            (m for m in user.memberships if m.tenant_id == token_tenant_id and m.status == "active"),
            None,
        )
        if membership:
            user.active_tenant_id = token_tenant_id
            user.active_role = membership.role
        elif user.is_platform_admin:
            user.active_tenant_id = token_tenant_id
            user.active_role = "platform_admin"
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant membership revoked")
    else:
        user.active_tenant_id = None
        user.active_role = "platform_admin" if user.is_platform_admin else None

    return user


async def get_tenant_context(
    request: Request,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    current_user: User = Depends(get_current_user),
) -> uuid.UUID:
    """Extracts tenant ID from header or active user context and sets ambient ContextVar."""
    tenant_id: Optional[uuid.UUID] = None

    if x_tenant_id:
        try:
            tenant_id = uuid.UUID(x_tenant_id)
        except ValueError:
            tenant_id = uuid.uuid5(uuid.NAMESPACE_DNS, str(x_tenant_id))
    elif current_user.active_tenant_id:
        tenant_id = current_user.active_tenant_id

    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing tenant context header")

    # Verify user has access to this tenant
    if not current_user.is_platform_admin:
        allowed = any(m.tenant_id == tenant_id and m.status == "active" for m in current_user.memberships)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found or access denied",
            )

    set_current_tenant_id(tenant_id)
    return tenant_id


def require_reviewer(current_user: User = Depends(get_current_user)) -> User:
    if current_user.is_platform_admin or getattr(current_user, "active_role", None) in (
        "reviewer",
        "tenant_admin",
        "platform_admin",
    ):
        return current_user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reviewer privileges required")


def require_platform_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.is_platform_admin:
        return current_user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform admin privileges required")
