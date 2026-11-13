# Security Guide

## Threat Model

### Assets to Protect

| Asset | Sensitivity | Storage |
|---|---|---|
| Identity documents (passport, ID scans) | **Critical** | MinIO (encrypted at rest) |
| OCR-extracted PII (names, DOB, ID numbers) | **High** | PostgreSQL (RLS-protected) |
| User credentials (passwords) | **Critical** | PostgreSQL (bcrypt hashed) |
| JWT tokens | **High** | HTTP-only cookies |
| Invitation tokens | **High** | Hashed in PostgreSQL |
| Audit logs | **High** | PostgreSQL (append-only) |
| Business registration data | **Medium** | PostgreSQL |

### Threat Categories

| Threat | Mitigation |
|---|---|
| Cross-tenant data access | PostgreSQL RLS + application filters + API authorization |
| Session hijacking | HTTP-only cookies, short expiry, secure flag |
| CSRF attacks | Double-submit cookie pattern |
| Document URL leaking | Pre-signed URLs with 5-min expiry, no public URLs |
| Privilege escalation | Backend role enforcement on every endpoint |
| SQL injection | SQLAlchemy ORM (parameterized queries), Pydantic validation |
| File upload attacks | Magic byte validation, size limits, malware scanning |
| Brute force login | Rate limiting with `slowapi` + Redis |
| Token replay | Short-lived JWTs, token rotation on sensitive actions |
| Insider data access | Audit logging, minimal PII in logs, no bulk export API |

---

## Authentication

### Password Security

```python
# Using passlib with bcrypt
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # Increase for production (default is 12)
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

### Password Requirements
- Minimum 8 characters
- At least 1 uppercase, 1 lowercase, 1 digit
- Validate with Pydantic validator, not just frontend
- Never log passwords, even hashed

### JWT Token Structure

```python
# Token payload
{
    "sub": "user-uuid",                    # User ID
    "tenant_id": "tenant-uuid",           # Active tenant
    "role": "reviewer",                    # Current role in tenant
    "exp": 1700000000,                     # Expiry (30 min)
    "iat": 1699998200,                     # Issued at
    "jti": "unique-token-id"              # For revocation tracking
}
```

### Cookie Configuration

```python
response.set_cookie(
    key="access_token",
    value=jwt_token,
    httponly=True,      # Cannot be read by JavaScript
    secure=True,        # Only sent over HTTPS
    samesite="lax",     # CSRF protection
    max_age=1800,       # 30 minutes
    path="/",           # Available to all paths
    domain=None,        # Current domain only
)
```

> [!CAUTION]
> **Never store JWT tokens in `localStorage` or `sessionStorage`.** These are accessible to any JavaScript running on the page, making them vulnerable to XSS attacks. HTTP-only cookies are the only secure option for browser-based auth.

---

## CSRF Protection

### Double-Submit Cookie Pattern

1. On login, set a random CSRF token in a **readable** cookie (not HTTP-only)
2. Frontend reads this cookie and sends it in the `X-CSRF-Token` header
3. Backend middleware compares the cookie value with the header value
4. Mismatch → 403 Forbidden

```python
# Backend: CSRF Middleware
class CSRFMiddleware(BaseHTTPMiddleware):
    EXEMPT_METHODS = {"GET", "HEAD", "OPTIONS"}
    EXEMPT_PATHS = {"/api/v1/auth/login", "/docs", "/openapi.json", "/health"}
    
    async def dispatch(self, request, call_next):
        if request.method in self.EXEMPT_METHODS:
            return await call_next(request)
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        cookie_token = request.cookies.get("csrf_token")
        header_token = request.headers.get("X-CSRF-Token")
        
        if not cookie_token or not header_token:
            raise HTTPException(403, "CSRF token missing")
        if not secrets.compare_digest(cookie_token, header_token):
            raise HTTPException(403, "CSRF token mismatch")
        
        return await call_next(request)
```

```typescript
// Frontend: Attach CSRF token to all mutations
function getCsrfToken(): string {
  const match = document.cookie.match(/csrf_token=([^;]+)/);
  return match ? match[1] : "";
}

const apiClient = {
  post: (url: string, data: any) =>
    fetch(url, {
      method: "POST",
      credentials: "include",  // Send cookies
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": getCsrfToken(),
      },
      body: JSON.stringify(data),
    }),
};
```

---

## Document Security

### Upload Validation Pipeline

```
1. Check Content-Length header (reject > 10MB immediately)
2. Read first 2048 bytes → validate magic bytes (python-magic)
3. Cross-check detected MIME vs. file extension
4. Compute SHA-256 hash of entire file
5. Check hash against known uploads (deduplication)
6. Upload to MinIO "unscanned/" prefix
7. Enqueue virus scan via Celery
8. On scan pass → move to "documents/" prefix
9. On scan fail → move to "quarantine/" + alert admin
```

### Magic Byte Validation

```python
import magic

ALLOWED_MIMES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}

EXTENSION_MAP = {
    "application/pdf": [".pdf"],
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
}

def validate_file(file_bytes: bytes, original_filename: str) -> str:
    """Validate file content matches allowed types. Returns detected MIME."""
    detected_mime = magic.from_buffer(file_bytes[:2048], mime=True)
    
    if detected_mime not in ALLOWED_MIMES:
        raise ValueError(f"File type '{detected_mime}' is not allowed")
    
    # Cross-check extension
    ext = Path(original_filename).suffix.lower()
    allowed_extensions = EXTENSION_MAP.get(detected_mime, [])
    if ext not in allowed_extensions:
        raise ValueError(f"Extension '{ext}' does not match detected type '{detected_mime}'")
    
    return detected_mime
```

### MinIO Storage Layout

```
bucket: ckyc-documents
├── tenants/
│   ├── {tenant_id_1}/
│   │   ├── cases/
│   │   │   ├── {case_id}/
│   │   │   │   ├── {uuid1}-passport.pdf
│   │   │   │   └── {uuid2}-trade_license.pdf
│   │   └── unscanned/
│   │       └── {uuid3}-pending.pdf
│   └── {tenant_id_2}/
│       └── ...
└── quarantine/
    └── {uuid}-infected.pdf
```

### Pre-Signed URL Security

```python
def generate_download_url(
    storage_key: str,
    tenant_id: str,
    user_id: str,
    case_id: str,
) -> str:
    """Generate a short-lived download URL after authorization checks."""
    # 1. Verify storage_key starts with correct tenant prefix
    expected_prefix = f"tenants/{tenant_id}/"
    if not storage_key.startswith(expected_prefix):
        raise PermissionError("Storage key does not belong to this tenant")
    
    # 2. Generate pre-signed URL (5-minute expiry)
    url = minio_client.presigned_get_object(
        bucket_name="ckyc-documents",
        object_name=storage_key,
        expires=timedelta(minutes=5),
        response_headers={
            "response-content-disposition": f'inline; filename="document"',
        },
    )
    
    # 3. Log the access
    audit_service.log(
        actor_id=user_id,
        tenant_id=tenant_id,
        object_type="document",
        object_id=case_id,
        action="download_url_generated",
    )
    
    return url
```

> [!WARNING]
> **The Docker hostname trap:** If MinIO runs in Docker as `minio:9000`, pre-signed URLs will contain `http://minio:9000/...` which the browser cannot resolve. Use an environment variable `MINIO_PUBLIC_ENDPOINT` for URLs returned to clients.

### Encryption at Rest

```yaml
# docker-compose.yml — MinIO with auto-encryption
minio:
  image: minio/minio:latest
  environment:
    MINIO_ROOT_USER: ${MINIO_ROOT_USER}
    MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    MINIO_KMS_AUTO_ENCRYPTION: "on"  # Auto-encrypt all objects
```

For production with external KMS (HashiCorp Vault):
```yaml
environment:
  MINIO_KMS_KES_ENDPOINT: "https://kes:7373"
  MINIO_KMS_KES_KEY_NAME: "ckyc-document-key"
```

---

## Rate Limiting

### Configuration

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://redis:6379/2",
    default_limits=["100/minute"],  # Global default
)

# Endpoint-specific limits
RATE_LIMITS = {
    "login": "5/minute",           # Prevent brute force
    "invitation": "5/minute",      # Prevent invitation spam
    "document_upload": "20/hour",  # Prevent abuse
    "password_reset": "3/hour",    # Prevent enumeration
}
```

---

## Audit Logging

### What to Log

| Action | Log? | Include |
|---|---|---|
| Login success/failure | ✅ | user_id, IP, user_agent |
| Case created/updated | ✅ | case_id, status change |
| Document uploaded | ✅ | document_id, file_hash (NOT content) |
| Document viewed/downloaded | ✅ | document_id, accessor |
| OCR completed | ✅ | document_id, field count |
| Share granted/revoked | ✅ | share_id, parties, fields |
| User role changed | ✅ | user_id, old_role, new_role |
| Tenant created | ✅ | tenant_id, creator |

### What to NEVER Log

| Data | Reason |
|---|---|
| Passwords (even hashed) | Security |
| JWT tokens | Session hijacking risk |
| Full ID numbers | PII exposure |
| Document contents/bytes | Data volume + privacy |
| OCR full text output | PII exposure |
| File download URLs | Pre-signed URL leakage |

### Audit Service Implementation

```python
class AuditService:
    async def log(
        self,
        db: AsyncSession,
        actor_id: Optional[str],
        tenant_id: Optional[str],
        object_type: str,
        object_id: str,
        action: str,
        metadata: Optional[dict] = None,
        request: Optional[Request] = None,
    ):
        event = AuditEvent(
            actor_id=actor_id,
            tenant_id=tenant_id,
            object_type=object_type,
            object_id=object_id,
            action=action,
            metadata=metadata,
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent", "")[:500] if request else None,
        )
        db.add(event)
        # Don't flush here — let the caller's transaction commit handle it
```

---

## Invitation & Sharing Token Security

### Token Lifecycle

```
1. Generate random token with `itsdangerous.URLSafeTimedSerializer`
2. Compute SHA-256 hash of the token
3. Store ONLY the hash in the database (never the raw token)
4. Send the raw token to the applicant (via email/notification)
5. On use: hash the received token and compare against stored hash
6. Mark as used after successful verification (prevent replay)
7. Token expires after 48 hours (configurable)
```

### Implementation

```python
from itsdangerous import URLSafeTimedSerializer
import hashlib

serializer = URLSafeTimedSerializer(SECRET_KEY)

def create_secure_token(payload: dict, salt: str) -> tuple[str, str]:
    """Returns (raw_token, token_hash) — store only the hash."""
    raw_token = serializer.dumps(payload, salt=salt)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, token_hash

def verify_secure_token(raw_token: str, stored_hash: str, salt: str, max_age: int = 172800) -> dict:
    """Verify token against stored hash and time limit."""
    computed_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    if not secrets.compare_digest(computed_hash, stored_hash):
        raise HTTPException(400, "Invalid token")
    return serializer.loads(raw_token, salt=salt, max_age=max_age)
```

---

## Environment Variables Security

### `.env.example` (Placeholder Values Only)

```env
# Database
POSTGRES_USER=ckyc_user
POSTGRES_PASSWORD=CHANGE_ME_IN_PRODUCTION
POSTGRES_DB=ckyc_db
DATABASE_URL=postgresql+asyncpg://ckyc_user:CHANGE_ME@postgres:5432/ckyc_db

# Redis
REDIS_URL=redis://redis:6379/0

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=CHANGE_ME_IN_PRODUCTION
MINIO_ENDPOINT=minio:9000
MINIO_PUBLIC_ENDPOINT=http://localhost:9000
MINIO_SECURE=false

# Auth
SECRET_KEY=CHANGE_ME_TO_A_RANDOM_STRING_IN_PRODUCTION
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OCR
OCR_ADAPTER=mock  # mock | tesseract | google_vision

# Email
EMAIL_ADAPTER=mock  # mock | imap

# Frontend
FRONTEND_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000
```

> [!CAUTION]
> **Never commit real secrets to version control.** The `.env.example` file should contain only placeholder values. Actual secrets should be provided via environment variables, secret managers (Vault, AWS Secrets Manager), or CI/CD pipeline secrets.

---

## Security Testing Checklist

### Tenant Isolation Tests

```python
async def test_tenant_a_cannot_access_tenant_b_cases(client, tenant_a_token, tenant_b_case):
    """A user in Tenant A must not see Tenant B's cases."""
    response = await client.get(
        f"/api/v1/cases/{tenant_b_case.id}",
        cookies={"access_token": tenant_a_token},
    )
    assert response.status_code == 404  # Not 403 (don't reveal existence)

async def test_tenant_a_cannot_download_tenant_b_documents(client, tenant_a_token, tenant_b_doc):
    """A user in Tenant A must not get download URLs for Tenant B's documents."""
    response = await client.get(
        f"/api/v1/documents/{tenant_b_doc.id}/download",
        cookies={"access_token": tenant_a_token},
    )
    assert response.status_code == 404

async def test_rls_blocks_cross_tenant_query(db_session_tenant_a, case_in_tenant_b):
    """Even a raw query should not return another tenant's data."""
    result = await db_session_tenant_a.execute(
        select(KycCase).where(KycCase.id == case_in_tenant_b.id)
    )
    assert result.scalar_one_or_none() is None
```

### Role Permission Tests

```python
async def test_reviewer_cannot_create_tenant(client, reviewer_token):
    response = await client.post(
        "/api/v1/tenants",
        json={"name": "Evil Tenant"},
        cookies={"access_token": reviewer_token},
    )
    assert response.status_code == 403

async def test_applicant_cannot_approve_case(client, applicant_token, case_id):
    response = await client.post(
        f"/api/v1/cases/{case_id}/approve",
        json={"reason": "Self-approve"},
        cookies={"access_token": applicant_token},
    )
    assert response.status_code == 403
```

### Share Security Tests

```python
async def test_expired_share_returns_nothing(client, recipient_token, expired_share):
    response = await client.get(
        f"/api/v1/shares/{expired_share.id}",
        cookies={"access_token": recipient_token},
    )
    assert response.status_code == 410  # Gone

async def test_revoked_share_returns_nothing(client, recipient_token, revoked_share):
    response = await client.get(
        f"/api/v1/shares/{revoked_share.id}",
        cookies={"access_token": recipient_token},
    )
    assert response.status_code == 410
```
