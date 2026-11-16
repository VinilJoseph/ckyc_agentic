"""Security & Cryptographic Utilities: Password Hashing, JWT & CSRF Tokens."""
from datetime import datetime, timedelta
import secrets
from typing import Any, Dict, Optional, Union
import uuid

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, uuid.UUID],
    tenant_id: Optional[Union[str, uuid.UUID]] = None,
    role: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "type": "access",
    }
    if tenant_id:
        to_encode["tenant_id"] = str(tenant_id)
    if role:
        to_encode["role"] = role

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)
