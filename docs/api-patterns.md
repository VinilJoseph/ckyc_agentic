# API Patterns & Best Practices

## FastAPI Multi-Tenancy Implementation

### Tenant Context Propagation

Use Python's `contextvars` for async-safe tenant context across concurrent requests:

```python
# app/core/context.py
from contextvars import ContextVar
from typing import Optional

_tenant_id_ctx: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)

def get_current_tenant_id() -> str:
    tenant_id = _tenant_id_ctx.get()
    if not tenant_id:
        raise ValueError("Tenant context is not set!")
    return tenant_id

def set_current_tenant_id(tenant_id: str):
    return _tenant_id_ctx.set(tenant_id)
```

### Tenant-Scoped Database Session

```python
# app/core/database.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import event, text
from app.core.context import _tenant_id_ctx

engine = create_async_engine(
    "postgresql+asyncpg://app_user:password@postgres:5432/ckyc",
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False,
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Inject tenant context into every transaction
@event.listens_for(engine.sync_engine, "begin")
def set_tenant_context(conn):
    tenant_id = _tenant_id_ctx.get()
    if tenant_id:
        conn.exec_driver_sql(
            "SELECT set_config('app.current_tenant', %s, true)",
            (str(tenant_id),)
        )
    else:
        conn.exec_driver_sql(
            "SELECT set_config('app.current_tenant', '', true)"
        )
```

> [!CAUTION]
> **Always use `SET LOCAL` or `set_config(..., true)`** (transaction-scoped). Never use `SET` (connection-scoped) — connection pooling will leak tenant state between requests.

### FastAPI Dependency Chain

```python
# app/core/dependencies.py
from fastapi import Depends, HTTPException, Request
from app.core.security import verify_jwt_cookie
from app.core.context import set_current_tenant_id
from app.core.database import async_session_maker

async def get_current_user(request: Request) -> User:
    """Extract user from JWT in HTTP-only cookie."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = verify_jwt_cookie(token)
    # ... fetch user from DB
    return user

async def get_tenant_context(user: User = Depends(get_current_user)) -> str:
    """Set tenant context from JWT claims — never from client params."""
    tenant_id = user.active_tenant_id
    set_current_tenant_id(tenant_id)
    return tenant_id

async def get_db(
    tenant_id: str = Depends(get_tenant_context),
) -> AsyncSession:
    """Provide a tenant-scoped DB session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

---

## Authentication Implementation

### JWT + HTTP-Only Cookie Pattern

```python
# app/core/security.py
import secrets
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Response

SECRET_KEY = "your-secret-key-from-env"  # Load from env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_jwt_cookie(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### Login Endpoint with CSRF Protection

```python
@router.post("/api/v1/auth/login")
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token_data = {
        "sub": str(user.id),
        "tenant_id": str(user.active_tenant_id),
        "role": user.role.value,
    }
    access_token = create_access_token(token_data)
    csrf_token = secrets.token_hex(32)
    
    # JWT in HTTP-only cookie (not accessible to JS)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,       # HTTPS only
        samesite="lax",    # CSRF protection
        max_age=1800,      # 30 minutes
    )
    # CSRF token in readable cookie (for double-submit pattern)
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,     # JS needs to read this
        secure=True,
        samesite="lax",
    )
    return {"message": "Logged in", "user": UserResponse.from_orm(user)}
```

### CSRF Middleware (Double-Submit Cookie)

```python
# app/core/csrf.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

EXEMPT_METHODS = {"GET", "HEAD", "OPTIONS"}
EXEMPT_PATHS = {"/api/v1/auth/login", "/api/v1/auth/register", "/docs", "/openapi.json"}

class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in EXEMPT_METHODS:
            return await call_next(request)
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)
        
        cookie_token = request.cookies.get("csrf_token")
        header_token = request.headers.get("X-CSRF-Token")
        
        if not cookie_token or not header_token or cookie_token != header_token:
            raise HTTPException(status_code=403, detail="CSRF validation failed")
        
        return await call_next(request)
```

---

## Role-Based Access Control (RBAC)

### Role Checker Dependency Factory

```python
# app/core/rbac.py
from enum import Enum
from fastapi import Depends, HTTPException

class RoleEnum(str, Enum):
    PLATFORM_ADMIN = "platform_admin"
    TENANT_ADMIN = "tenant_admin"
    REVIEWER = "reviewer"
    APPLICANT = "applicant"
    RECIPIENT = "recipient"

class RoleChecker:
    """Reusable dependency that checks if the current user has an allowed role."""
    def __init__(self, allowed_roles: list[RoleEnum]):
        self.allowed_roles = allowed_roles
    
    def __call__(self, user: User = Depends(get_current_user)) -> User:
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{user.role}' is not authorized for this action"
            )
        return user

# Pre-built checkers for common patterns
require_platform_admin = RoleChecker([RoleEnum.PLATFORM_ADMIN])
require_tenant_admin = RoleChecker([RoleEnum.PLATFORM_ADMIN, RoleEnum.TENANT_ADMIN])
require_reviewer = RoleChecker([RoleEnum.TENANT_ADMIN, RoleEnum.REVIEWER])
require_applicant = RoleChecker([RoleEnum.APPLICANT])
```

### Usage in Endpoints

```python
@router.post("/api/v1/tenants", dependencies=[Depends(require_platform_admin)])
async def create_tenant(data: CreateTenantRequest, db: AsyncSession = Depends(get_db)):
    # Only platform admins can reach here
    ...

@router.get("/api/v1/cases")
async def list_cases(
    user: User = Depends(require_reviewer),  # Tenant admins and reviewers
    db: AsyncSession = Depends(get_db),
):
    # RLS automatically scopes to user's tenant
    cases = await case_service.list_cases(db, filters=...)
    return cases
```

---

## Invitation Token Flow

### Using `itsdangerous` for Time-Limited Tokens

```python
# app/core/tokens.py
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

serializer = URLSafeTimedSerializer(SECRET_KEY)

def create_invitation_token(case_id: str, applicant_id: str) -> str:
    """Create a time-limited invitation token (48 hours)."""
    return serializer.dumps(
        {"case_id": case_id, "applicant_id": applicant_id},
        salt="case-invitation"
    )

def verify_invitation_token(token: str) -> dict:
    """Verify and decode an invitation token."""
    try:
        return serializer.loads(token, salt="case-invitation", max_age=172800)  # 48 hours
    except SignatureExpired:
        raise HTTPException(status_code=410, detail="Invitation has expired")
    except BadSignature:
        raise HTTPException(status_code=400, detail="Invalid invitation token")
```

### Invitation Endpoint

```python
@router.post("/api/v1/cases/{case_id}/invite")
async def invite_applicant(
    case_id: str,
    data: InviteRequest,
    user: User = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db),
):
    case = await case_service.get_case(db, case_id)
    token = create_invitation_token(case_id, str(case.applicant_id))
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    # Store hash only — never the raw token
    await db.execute(
        insert(InvitationToken).values(
            case_id=case_id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(hours=48),
        )
    )
    
    # Send notification (mock in dev)
    invitation_url = f"{FRONTEND_URL}/invitation?token={token}"
    await notification_service.send_invitation(data.email, invitation_url)
    
    return {"message": "Invitation sent", "expires_in": "48 hours"}
```

---

## API Response Patterns

### Standard Response Schema

```python
# app/schemas/common.py
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, List

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    has_next: bool
```

### Error Handling

```python
# app/core/exceptions.py
from fastapi import Request
from fastapi.responses import JSONResponse

class AppException(Exception):
    def __init__(self, status_code: int, detail: str, error_code: str = None):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code

class TenantAccessDenied(AppException):
    def __init__(self):
        super().__init__(403, "Access denied to this tenant's resources", "TENANT_ACCESS_DENIED")

class CaseNotFound(AppException):
    def __init__(self, case_id: str):
        super().__init__(404, f"Case not found", "CASE_NOT_FOUND")

# Global exception handler
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {"code": exc.error_code, "detail": exc.detail},
        },
    )
```

---

## Rate Limiting

### Using `slowapi` with Redis

```python
# app/core/rate_limit.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://redis:6379/2",
)

# Apply to sensitive endpoints
@router.post("/api/v1/cases/{case_id}/invite")
@limiter.limit("5/minute")  # Max 5 invitations per minute per IP
async def invite_applicant(request: Request, ...):
    ...

@router.post("/api/v1/cases/{case_id}/documents")
@limiter.limit("20/hour")  # Max 20 uploads per hour per IP
async def upload_document(request: Request, ...):
    ...
```

---

## OpenAPI Documentation

### API Versioning and Tags

```python
# app/main.py
from fastapi import FastAPI

app = FastAPI(
    title="CKYC Marketplace API",
    description="Multi-tenant KYC case management for electronic marketplaces",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Router aggregation with tags
from app.api.v1.endpoints import auth, cases, documents, sharing, tenants, users

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(tenants.router, prefix="/api/v1/tenants", tags=["Tenants"])
app.include_router(cases.router, prefix="/api/v1/cases", tags=["Cases"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(sharing.router, prefix="/api/v1/shares", tags=["Sharing"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
```

---

## Background Task Integration

### Enqueuing Celery Tasks from FastAPI

```python
# app/services/document_service.py
from app.workers.tasks import process_document_pipeline

async def handle_document_upload(
    db: AsyncSession,
    case_id: str,
    tenant_id: str,
    file: UploadFile,
) -> CaseDocument:
    # 1. Validate file
    validated_mime = validate_file_content(file.file, ALLOWED_MIMES)
    
    # 2. Upload to MinIO
    storage_key = f"tenants/{tenant_id}/cases/{case_id}/{uuid4()}"
    await storage_service.upload(file.file, storage_key)
    
    # 3. Create DB record
    document = CaseDocument(
        case_id=case_id,
        storage_key=storage_key,
        original_filename=file.filename,
        file_hash=compute_sha256(file.file),
        source="portal",
        review_status="pending",
    )
    db.add(document)
    await db.flush()  # Get ID before commit
    
    # 4. Enqueue background processing
    process_document_pipeline.delay(
        document_id=str(document.id),
        storage_key=storage_key,
        tenant_id=tenant_id,
    )
    
    # 5. Update case status
    await case_service.transition_status(db, case_id, "documents_received")
    
    return document
```

> [!IMPORTANT]
> **Never pass file bytes through Celery/Redis.** Always store the file in MinIO first, then pass only the `storage_key` to the Celery task. This prevents Redis bloat and keeps task payloads small.
