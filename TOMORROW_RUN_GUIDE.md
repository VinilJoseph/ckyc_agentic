# CKYC Marketplace MVP — Resume & Run Guide for Tomorrow

> **Saved on:** November 12, 2026  
> **Status:** Planning, research, documentation, UI system, and multi-agent task prompt are **100% prepared**. Everything is ready to execute.

---

## 1. Quick Summary of Current State

All research, architecture, schemas, and UI design rules have been prepared in your workspace:

| Document | Location | Purpose |
|---|---|---|
| **Product Intent** | [`intent.md`](file:///C:/Users/trainee1/Documents/trainee_notes/ckyc_agentic/intent.md) | Full MVP scope, golden path priority, P0/P1/P2 breakdown |
| **UI Design System** | [`docs/ui-design-system.md`](file:///C:/Users/trainee1/Documents/trainee_notes/ckyc_agentic/docs/ui-design-system.md) | **Light mode** (`design1-3`: fintech canvas, cyan/teal holographic accents) vs **Dark mode** (`design4`: obsidian `#0D0D10`, wireframe lines, stark white pill buttons) |
| **Sprint Plan** | [`docs/mvp-implementation-plan.md`](file:///C:/Users/trainee1/Documents/trainee_notes/ckyc_agentic/docs/mvp-implementation-plan.md) | Sprints 1–3 Golden Path + Sprints 4–5, test requirements, demo script |
| **System Architecture** | [`docs/architecture.md`](file:///C:/Users/trainee1/Documents/trainee_notes/ckyc_agentic/docs/architecture.md) | Docker Compose topology, Celery worker pipeline, MinIO private storage |
| **Data Model & RLS** | [`docs/data-model.md`](file:///C:/Users/trainee1/Documents/trainee_notes/ckyc_agentic/docs/data-model.md) | All 13 SQLAlchemy models + PostgreSQL Row-Level Security policies |
| **API & Auth Patterns** | [`docs/api-patterns.md`](file:///C:/Users/trainee1/Documents/trainee_notes/ckyc_agentic/docs/api-patterns.md) | FastAPI async, HttpOnly JWT cookies, CSRF double-submit, RBAC |
| **Security Guide** | [`docs/security-guide.md`](file:///C:/Users/trainee1/Documents/trainee_notes/ckyc_agentic/docs/security-guide.md) | Threat model, magic-byte file validation, audit logging, isolation tests |

---

## 2. Option A: How to Run with Multi-Agent Teamwork Tomorrow

When you start tomorrow, you can immediately trigger the multi-agent build with zero interview delay by sending this single prompt:

```text
/teamwork [skip-interview] Build the CKYC Marketplace MVP following intent.md, docs/mvp-implementation-plan.md (Sprints 1-3 Golden Path), docs/ui-design-system.md (Light mode designs 1-3, Dark mode design 4), and all docs in the docs folder.
```

Using `[skip-interview]` allows the agent team to start scaffolding and coding immediately without waiting for questions.

---

## 3. Option B: Step-by-Step Manual / Phased Build Walkthrough

If you prefer building or monitoring phase by phase, follow this exact sequence:

### Phase 1: Infrastructure & Database Scaffold (Sprint 1)
1. **Create Docker Compose environment**:
   - `postgres:15-alpine` (with `app_owner` for Alembic, `app_user` for FastAPI runtime)
   - `redis:7-alpine` (Celery broker + rate limiter)
   - `minio/minio` (S3 private document storage, auto-create `ckyc-documents` bucket)
   - `api` (FastAPI + Uvicorn)
   - `celery-worker` (Background processing)
   - `frontend` (Vite + React 18 + TypeScript + Tailwind)
2. **Apply Alembic Migrations**:
   - Create tables: `tenants`, `users`, `tenant_memberships`, `applicants`, `kyc_cases`, `case_documents`, `extracted_fields`, `share_grants`, `audit_events`.
   - Apply PostgreSQL RLS policies with `ALTER TABLE ... FORCE ROW LEVEL SECURITY;`.
3. **Set Up Auth & Multi-Tenancy**:
   - JWT in HttpOnly cookies (`access_token`, 30 min expiry).
   - Double-submit CSRF cookie (`csrf_token`).
   - Session context injection (`SET LOCAL app.current_tenant = ...`).
   - RBAC dependency factory (`require_platform_admin`, `require_tenant_admin`, `require_reviewer`).

### Phase 2: Core Golden Path & Document Pipeline (Sprint 2)
1. **Case State Machine**:
   - Statuses: `draft` $\rightarrow$ `invitation_sent` $\rightarrow$ `awaiting_documents` $\rightarrow$ `documents_received` $\rightarrow$ `ocr_processing` $\rightarrow$ `in_review` $\rightarrow$ `approved` / `rejected`.
2. **Document Upload & Storage**:
   - File validation via magic bytes (`python-magic`: PDF, PNG, JPEG only, max 10MB).
   - Upload stream to MinIO private path: `tenants/{tenant_id}/cases/{case_id}/{uuid}-{filename}`.
   - Generate short-lived (5 min) pre-signed download URLs.
3. **Mock OCR Celery Pipeline**:
   - Background worker task receives `storage_key` and extracts structured draft fields (Company Name, Registration No, Issue Date, Tax ID, Signatory).
   - Updates status to `in_review`.

### Phase 3: Applicant Portal & Controlled Sharing (Sprint 3)
1. **Applicant Invitation Flow**:
   - Generate time-limited secure token using `itsdangerous` (48-hour TTL, hashed in DB).
   - Applicant lands on portal without login, scoped strictly to their case.
2. **Reviewer Workspace**:
   - 55/45 split view (document viewer on left, OCR draft fields on right).
   - Reviewer can confirm, edit, or reject fields. Mandatory decision rationale for final approval.
3. **Controlled Peer Data Sharing**:
   - Recipient tenant requests specific fields for a stated purpose.
   - Applicant reviews and grants/declines consent.
   - Recipient sees *only* approved claims and verification status (never raw document files).

### Phase 4: Frontend Theming & Polish
1. **Dual Theme Implementation**:
   - **Light Mode Toggle**: Clean white canvas (`#F8FAFC`), modern typography, holographic cyan/mint pill badges (`#00C2CB`), high-contrast slate callout cards (from `design1-3`).
   - **Dark Mode Toggle**: Sleek obsidian canvas (`#0D0D10`), elevated surfaces (`#16161A`), subtle wireframe gridlines, and stark white pill action buttons (from `design4`).
2. **Dashboard**:
   - Metric KPI cards, search, status filters, and interactive case inspection drawer.

---

## 4. Key Local Development Commands

```bash
# 1. Start all containers in background
docker compose up -d

# 2. View logs for API and Celery worker
docker compose logs -f api celery-worker

# 3. Run database migrations
docker compose exec api alembic upgrade head

# 4. Seed initial test tenants and users
docker compose exec api python -m app.scripts.seed_data

# 5. Run automated tests (isolation + golden path)
docker compose exec api pytest tests/ -v

# 6. Stop all containers (preserving database volume)
docker compose down

# 7. Reset completely (clean slate if needed)
docker compose down -v
```

---

## 5. Ready-to-Run Demo Script

When the build is done, you can run this exact 3-minute showcase demo:
1. **Platform Admin**: Log in $\rightarrow$ Create tenant *"Apex Supplies"*.
2. **Tenant Admin**: Create KYC Case `CASE-001` for *"Nova Tech"* $\rightarrow$ Generate applicant invitation link.
3. **Applicant**: Open invitation link in incognito tab $\rightarrow$ Upload sample registration document $\rightarrow$ Status transitions to `OCR Processing`.
4. **Celery Worker**: Completes mock OCR extraction $\rightarrow$ Status becomes `In Review`.
5. **Reviewer**: Open reviewer workspace $\rightarrow$ Inspect document + fields side-by-side $\rightarrow$ Confirm fields $\rightarrow$ Approve case.
6. **Controlled Share**: Create share grant to *"ThirdParty Bank"* for business registration verification $\rightarrow$ Applicant consents.
7. **Recipient View**: Log in as recipient $\rightarrow$ View verified credential badge with 30-day expiry.
8. **Theme Check**: Toggle from Light Mode (designs 1–3) to Dark Mode (design 4) to demonstrate visual excellence.
