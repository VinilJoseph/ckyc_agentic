# MVP Implementation Plan

## Overview

This plan breaks the MVP into **5 sprints** (each ~1 week). Sprint 1-3 delivers the golden path. Sprint 4-5 adds supporting features.

---

## Sprint 1: Foundation (Days 1-5)

**Goal:** Project scaffold, database, auth, multi-tenancy working end-to-end.

### Tasks

| # | Task | Est. Hours | Deliverable |
|---|---|---|---|
| 1.1 | Project scaffold (backend + frontend + Docker Compose) | 4h | Running dev environment |
| 1.2 | PostgreSQL + Alembic setup | 3h | Migration framework |
| 1.3 | Core models: Tenant, User, TenantMembership | 4h | Initial migration |
| 1.4 | RLS policies migration | 3h | Tenant isolation at DB level |
| 1.5 | Auth: login, JWT cookies, CSRF middleware | 6h | `/api/v1/auth/login`, `/logout` |
| 1.6 | RBAC dependency factory | 3h | Role-checked endpoints |
| 1.7 | Tenant context middleware | 3h | Auto-scoped DB sessions |
| 1.8 | Platform admin: create/list tenants | 4h | `/api/v1/tenants` CRUD |
| 1.9 | Seed data script | 2h | 2 tenants, 5 users, memberships |
| 1.10 | Frontend: Vite + React scaffold | 3h | Login page, basic layout |
| 1.11 | Tenant isolation tests | 3h | Proves cross-tenant blocking |

**Sprint 1 Definition of Done:**
- [x] `docker compose up` starts all services
- [x] User can log in, get JWT cookie
- [x] Platform admin can create tenants
- [x] RLS blocks cross-tenant queries (tested)
- [x] Frontend shows login page

### Docker Compose Setup

```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports: ["5432:5432"]
    volumes: [postgres_data:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    ports: ["9000:9000", "9001:9001"]
    command: server /data --console-address ":9001"
    volumes: [minio_data:/data]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      retries: 3

  api:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ports: ["8000:8000"]
    volumes: ["./backend:/app"]
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
      minio: { condition: service_healthy }
    env_file: .env

  celery-worker:
    build: ./backend
    command: celery -A app.celery_app worker --loglevel=info
    volumes: ["./backend:/app"]
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
    env_file: .env

  frontend:
    build: ./frontend
    command: npm run dev -- --host 0.0.0.0
    ports: ["3000:3000"]
    volumes: ["./frontend/src:/app/src"]

volumes:
  postgres_data:
  minio_data:
```

---

## Sprint 2: Case Workflow + Documents (Days 6-10)

**Goal:** Create cases, upload documents, mock OCR, reviewer workspace.

### Tasks

| # | Task | Est. Hours | Deliverable |
|---|---|---|---|
| 2.1 | Models: Applicant, KycCase, CaseDocument, ExtractedField | 5h | Migration |
| 2.2 | Case CRUD API | 4h | `/api/v1/cases` endpoints |
| 2.3 | Case status machine (transition validation) | 4h | Service layer + tests |
| 2.4 | MinIO storage abstraction | 3h | Upload/download service |
| 2.5 | Document upload endpoint (file validation, MinIO store) | 5h | `/api/v1/cases/{id}/documents` |
| 2.6 | Mock OCR adapter | 3h | Returns sample extracted fields |
| 2.7 | Celery OCR task pipeline | 4h | Upload → OCR → save fields |
| 2.8 | Case number generation | 1h | `CASE-0001` pattern |
| 2.9 | Frontend: Case list + filters | 5h | Dashboard with TanStack Query |
| 2.10 | Frontend: Case detail page | 4h | Document list, OCR fields |
| 2.11 | Frontend: Reviewer workspace | 5h | Confirm/correct/reject fields |
| 2.12 | Unit tests: case transitions, OCR field correction | 3h | Pytest |

**Sprint 2 Definition of Done:**
- [x] Tenant admin creates a case with an applicant
- [x] Documents upload to MinIO, hash validated
- [x] Mock OCR runs via Celery, produces extracted fields
- [x] Reviewer can confirm/correct/reject fields
- [x] Case status transitions correctly
- [x] Frontend shows case list, detail, reviewer workspace

### Case Status Machine Implementation

```python
# app/services/case_state_machine.py
VALID_TRANSITIONS = {
    CaseStatus.DRAFT: [CaseStatus.INVITATION_SENT, CaseStatus.EXPIRED],
    CaseStatus.INVITATION_SENT: [CaseStatus.AWAITING_DOCUMENTS, CaseStatus.EXPIRED],
    CaseStatus.AWAITING_DOCUMENTS: [CaseStatus.DOCUMENTS_RECEIVED, CaseStatus.EXPIRED],
    CaseStatus.DOCUMENTS_RECEIVED: [CaseStatus.OCR_PROCESSING],
    CaseStatus.OCR_PROCESSING: [CaseStatus.IN_REVIEW, CaseStatus.NEEDS_APPLICANT_CORRECTION],
    CaseStatus.NEEDS_APPLICANT_CORRECTION: [CaseStatus.IN_REVIEW],
    CaseStatus.IN_REVIEW: [
        CaseStatus.APPROVED,
        CaseStatus.REJECTED,
        CaseStatus.NEEDS_APPLICANT_CORRECTION,
    ],
    CaseStatus.APPROVED: [CaseStatus.CLOSED],
    CaseStatus.REJECTED: [CaseStatus.CLOSED],
}

def validate_transition(current: CaseStatus, target: CaseStatus) -> bool:
    allowed = VALID_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise InvalidTransitionError(
            f"Cannot transition from '{current}' to '{target}'. "
            f"Allowed: {allowed}"
        )
    return True
```

---

## Sprint 3: Invitation + Applicant Portal + Sharing (Days 11-15)

**Goal:** Complete the golden path end-to-end.

### Tasks

| # | Task | Est. Hours | Deliverable |
|---|---|---|---|
| 3.1 | Invitation token generation (itsdangerous) | 3h | Create + verify tokens |
| 3.2 | Applicant portal backend | 4h | Token auth, case access |
| 3.3 | Applicant document upload flow | 3h | Scoped to their case only |
| 3.4 | Applicant field correction endpoint | 3h | Correct OCR-extracted fields |
| 3.5 | ShareGrant model + API | 5h | Request/approve/decline/revoke |
| 3.6 | Applicant consent workflow | 4h | View request, approve/decline |
| 3.7 | Recipient share view endpoint | 3h | See only approved fields |
| 3.8 | Share expiry/revocation logic | 3h | Celery beat + checks |
| 3.9 | AuditEvent logging integration | 3h | All sensitive actions logged |
| 3.10 | Frontend: Applicant portal | 5h | Invitation landing, upload, consent |
| 3.11 | Frontend: Recipient share view | 3h | Read-only approved fields |
| 3.12 | E2E golden path test | 4h | Full flow automated |

**Sprint 3 Definition of Done:**
- [x] **Golden path works end-to-end:**
  1. Tenant admin creates case
  2. Applicant receives invitation (simulated)
  3. Applicant uploads document via portal
  4. OCR produces draft fields
  5. Reviewer confirms/corrects
  6. Applicant consents to share
  7. Recipient sees approved fields
- [x] Sharing respects expiry and revocation
- [x] Audit trail records all actions

---

## Sprint 4: Dashboard, Admin & Usage (Days 16-20)

**Goal:** Polish the UI, add admin features, usage tracking.

### Tasks

| # | Task | Est. Hours | Deliverable |
|---|---|---|---|
| 4.1 | Tenant dashboard with metrics | 4h | Case counts, status breakdown |
| 4.2 | Case search + advanced filters | 4h | Multi-field filtering |
| 4.3 | User/membership management | 4h | Invite users, assign roles |
| 4.4 | Subscription + usage tracking models | 3h | Plan limits, counters |
| 4.5 | Usage tracking service | 3h | Increment on case/doc/review |
| 4.6 | Platform admin tenant list | 3h | All tenants, status, usage |
| 4.7 | Frontend: Dashboard metrics cards | 4h | Independent TanStack Query widgets |
| 4.8 | Frontend: User management page | 4h | Invite, role assignment |
| 4.9 | Frontend: Usage/plan view | 3h | Current plan, limits, usage bars |
| 4.10 | Empty states + loading skeletons | 3h | Polish all pages |
| 4.11 | API documentation cleanup | 2h | OpenAPI descriptions |

**Sprint 4 Definition of Done:**
- [x] Dashboard shows real-time metrics
- [x] Cases searchable and filterable
- [x] Tenant admin can manage users
- [x] Usage tracked per billing period
- [x] All pages have loading/empty/error states

---

## Sprint 5: Email Intake + Polish (Days 21-25)

**Goal:** Add email intake, comprehensive tests, documentation.

### Tasks

| # | Task | Est. Hours | Deliverable |
|---|---|---|---|
| 5.1 | Email adapter interface (ABC) | 2h | Protocol definition |
| 5.2 | Mock email adapter (.eml import) | 3h | Parse .eml files |
| 5.3 | MailIngestionRecord model | 2h | Migration |
| 5.4 | Email → case matching service | 4h | Subject line parsing |
| 5.5 | Exception queue for unmatched emails | 3h | Admin can manually assign |
| 5.6 | Frontend: email exception queue | 3h | Admin page |
| 5.7 | Comprehensive test suite | 6h | All security + isolation tests |
| 5.8 | Seed data enrichment | 2h | Realistic fictional scenarios |
| 5.9 | README documentation | 4h | Setup, config, deployment notes |
| 5.10 | Known limitations doc | 2h | What's missing, next steps |
| 5.11 | Docker Compose optimization | 2h | Build caching, health checks |

**Sprint 5 Definition of Done:**
- [x] Email .eml import works through case workflow
- [x] Unmatched emails go to exception queue
- [x] All security tests pass
- [x] README covers complete setup
- [x] Known limitations documented

---

## Key Dependencies & Library Versions

### Backend (`requirements.txt`)

```
# Core
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0

# Database
sqlalchemy[asyncio]>=2.0.25
asyncpg>=0.29.0
alembic>=1.13.0

# Auth
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
itsdangerous>=2.1.2

# Task Queue
celery>=5.3.0
redis>=5.0.0
flower>=2.0.0

# Storage
minio>=7.2.0

# File Validation
python-magic>=0.4.27

# OCR (dev only)
pytesseract>=0.3.10
Pillow>=10.0.0

# Rate Limiting
slowapi>=0.1.9

# Testing
pytest>=7.4.0
pytest-asyncio>=0.23.0
httpx>=0.26.0  # For FastAPI test client
factory-boy>=3.3.0
```

### Frontend (`package.json` dependencies)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.21.0",
    "@tanstack/react-query": "^5.17.0",
    "react-hook-form": "^7.49.0",
    "@hookform/resolvers": "^3.3.0",
    "zod": "^3.22.0",
    "@radix-ui/react-dialog": "^1.0.0",
    "@radix-ui/react-dropdown-menu": "^2.0.0",
    "@radix-ui/react-tabs": "^1.0.0",
    "@radix-ui/react-toast": "^1.1.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.2.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "@testing-library/react": "^14.1.0",
    "vitest": "^1.1.0"
  }
}
```

---

## Demo Script

### Happy Path Demo (3 minutes)

```
1. [Platform Admin] Log in → Create a new tenant "Acme Trading LLC"
2. [Tenant Admin] Switch to Acme → Create a KYC case for "John Doe" (individual)
   → Set purpose: "Seller verification for marketplace access"
3. [Tenant Admin] Send invitation to applicant
4. [Applicant] Open invitation link → See tenant name + purpose
   → Upload passport (PDF) → See "Processing..." status
5. [System] Celery runs mock OCR → Extracts: name, DOB, passport number
   → Case auto-transitions to "In Review"
6. [Reviewer] Open case → See document + extracted fields side-by-side
   → Correct one field → Approve case with reason
7. [Tenant Admin] Create share request → Select fields to share with "Beta Corp"
   → Set purpose: "Supplier verification" → Set 30-day expiry
8. [Applicant] See share request → Review fields + purpose → Approve
9. [Recipient] Log in as Beta Corp → See shared verification:
   ✅ Name: John Doe | ✅ Verified: 2024-01-15 | ⏱️ Expires: 2024-02-15
10. [Platform Admin] View tenant list → See Acme's usage: 1 case, 1 document, 1 review
```

### Edge Case Demo (2 minutes)

```
1. [Cross-tenant test] Log in as Tenant B user → Try to access Tenant A case
   → 404 (not found, not 403)
2. [Expired share] Fast-forward time → Try to access expired share
   → 410 Gone
3. [Revoked share] Applicant revokes consent → Recipient loses access immediately
4. [Blurry document] Upload a blurry image → OCR extracts with low confidence
   → Reviewer requests applicant correction → Applicant resubmits
5. [Audit trail] Open any case → Full timeline of every action
```

---

## Known Limitations (MVP)

| Area | Limitation | Future Enhancement |
|---|---|---|
| Auth | No MFA/2FA | Add TOTP or WebAuthn |
| Auth | No SSO/SAML | Integrate with identity providers |
| OCR | Mock only (no real extraction) | Integrate Tesseract or cloud OCR |
| Email | .eml import only (no live IMAP) | Add IMAP polling with OAuth2 |
| Billing | Usage tracking only (no payments) | Integrate Stripe/Paddle |
| Scanning | No actual virus scanning | Integrate ClamAV |
| Notifications | Console output only | Email/SMS/webhook notifications |
| Search | Basic DB queries | Full-text search (pg_trgm or Elasticsearch) |
| Encryption | MinIO SSE only | Application-level field encryption |
| Compliance | No specific regulatory mapping | Add GDPR/AML compliance modules |
| Monitoring | Basic logging | Structured logging, APM, error tracking |
| Deployment | Docker Compose only | Kubernetes, CI/CD pipeline |


/teamwork 