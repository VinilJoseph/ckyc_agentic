"""Request Context & Tenant Scoping via Python contextvars."""
import uuid
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Generator, Optional, Union


class TenantContextMissingError(Exception):
    """Raised when tenant context is required but has not been set."""
    pass


class CrossTenantAccessException(Exception):
    """Raised when a cross-tenant data access violation is detected."""
    pass


_tenant_id_ctx: ContextVar[Optional[uuid.UUID]] = ContextVar("tenant_id", default=None)
_user_id_ctx: ContextVar[Optional[uuid.UUID]] = ContextVar("user_id", default=None)
_user_role_ctx: ContextVar[Optional[str]] = ContextVar("user_role", default=None)


def get_current_tenant_id() -> uuid.UUID:
    tenant_id = _tenant_id_ctx.get()
    if tenant_id is None:
        raise TenantContextMissingError("Tenant context is not set in the current execution scope.")
    return tenant_id


def get_current_tenant_id_optional() -> Optional[uuid.UUID]:
    return _tenant_id_ctx.get()


def set_current_tenant_id(tenant_id: Union[uuid.UUID, str]) -> Token[Optional[uuid.UUID]]:
    if isinstance(tenant_id, str):
        try:
            tenant_id = uuid.UUID(tenant_id)
        except (ValueError, AttributeError):
            tenant_id = uuid.uuid5(uuid.NAMESPACE_DNS, str(tenant_id))
    return _tenant_id_ctx.set(tenant_id)


def reset_current_tenant_id(token: Token[Optional[uuid.UUID]]) -> None:
    _tenant_id_ctx.reset(token)


@contextmanager
def tenant_context(tenant_id: Union[uuid.UUID, str]) -> Generator[uuid.UUID, None, None]:
    token = set_current_tenant_id(tenant_id)
    try:
        yield get_current_tenant_id()
    finally:
        reset_current_tenant_id(token)
