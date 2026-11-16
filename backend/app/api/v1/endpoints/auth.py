"""Authentication Router: Login, /me, Logout."""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, generate_csrf_token, verify_password
from app.models.tenant import TenantMembership
from app.models.user import User
from pydantic import BaseModel, EmailStr

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MessageResponse(BaseModel):
    message: str


@router.post("/login")
async def login(
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(User)
        .options(selectinload(User.memberships).selectinload(TenantMembership.tenant))
        .where(User.email == payload.email)
        .execution_options(bypass_tenant_isolation=True)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive.",
        )

    active_membership = next((m for m in user.memberships if m.status == "active"), None)
    active_tenant_id = active_membership.tenant_id if active_membership else None
    active_role = (
        active_membership.role
        if active_membership
        else ("platform_admin" if user.is_platform_admin else None)
    )

    token = create_access_token(
        subject=user.id,
        tenant_id=active_tenant_id,
        role=active_role,
    )
    csrf_token = generate_csrf_token()

    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    return {"access_token": token, "csrf_token": csrf_token, "user": {"id": user.id, "email": user.email, "role": active_role}}


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.active_role,
        "tenant_id": current_user.active_tenant_id,
    }


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response):
    response.delete_cookie(key=settings.COOKIE_NAME, path="/")
    response.delete_cookie(key=settings.CSRF_COOKIE_NAME, path="/")
    return MessageResponse(message="Logged out successfully")
