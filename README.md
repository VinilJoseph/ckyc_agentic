# CKYC / eKYC Marketplace Capability Showcase MVP

> Enterprise-grade, multi-tenant CKYC / eKYC pipeline showcasing automated document extraction, algorithmic KYC validation, selfie-to-ID biometric matching, email intake with exception triage, and an interactive dual-theme Reviewer SPA. Designed for rapid local execution with **zero Docker dependencies**.

---

## 🌟 Executive Overview

The **CKYC/eKYC Marketplace Showcase MVP** demonstrates an end-to-end, privacy-preserving digital identity lifecycle for modern fintech institutions. It streamlines customer onboarding, automates compliance verification against regulatory criteria, enables asynchronous document ingestion via email, and delivers an interactive reviewer decision workspace.

### Key Capabilities
- **Multi-Tenant Architecture**: Complete tenant isolation using SQLAlchemy `TenantMixin` enforced across 13 relational entities with row-level security and strict HTTP header validation (`X-Tenant-ID`).
- **Zero-Docker Lightweight Runtime**: Runs out of the box on Python 3.10+ using asynchronous FastAPI and SQLite WAL mode with zero container overhead.
- **Multi-Tier OCR Pipeline**: Fallback extraction engine supporting digital PDF text extraction via PyMuPDF (Tier 1), scanned image OCR via Tesseract (Tier 2), and vision model fallbacks (Tier 3).
- **Algorithmic KYC Validation Engine**: Strict algorithmic rule verification including UIDAI Verhoeff check digit validation, Income Tax Department PAN entity & checksum rules, ICAO 9303 Passport MRZ check digits, Indian Driving Licence state code checks, and fuzzy applicant name matching.
- **Selfie-to-ID Biometric Matching**: Cosine similarity face comparison between applicant live selfies and ID document photos with configurable confidence thresholds.
- **Email Document Intake & Exception Queue**: RFC 822 & MIME email parser supporting `[CASE-XXXX]` token identification, automatic attachment extraction, and an operational triage exception queue.
- **Interactive Reviewer SPA**: Split-view (55/45) reviewer workspace featuring inline document rendering, extracted field acceptance/correction controls, audit timeline stepper, sticky decision bar, and seamless Fintech Light vs. Obsidian Dark theme switching.

---

## 📐 Architecture & System Design

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Interactive Frontend (SPA)                            │
│   • 55/45 Split Reviewer Workspace  • Inline PDF / Image Document Viewer   │
│   • Field Decision Controls (Accept/Correct/Reject) • Sticky Action Bar     │
│   • Applicant Self-Service Portal   • Email Simulator Modal                 │
│   • Obsidian Dark / Fintech Light Dynamic Theme Engine                      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ REST / Async JSON
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                    FastAPI Async Application Backend                        │
│                                                                             │
│  ┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────┐  │
│  │  Authentication & RBAC │ │ Multi-Tenant Context  │ │  CSRF & CORS     │  │
│  │  JWT Bearer + Cookies  │ │ X-Tenant-ID Header    │ │  Double-Submit   │  │
│  └───────────────────────┘ └───────────────────────┘ └───────────────────┘  │
│                                                                             │
│  ┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────┐  │
│  │ 11-State KYC Lifecycle│ │ Multi-Tier OCR Engine │ │ Biometric Matcher │  │
│  │ Finite State Machine  │ │ PyMuPDF / Tesseract   │ │ Facial Cosine Sim │  │
│  └───────────────────────┘ └───────────────────────┘ └───────────────────┘  │
│                                                                             │
│  ┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────┐  │
│  │ KYC Validation Engine │ │ Email Ingestion Queue │ │ Controlled Share  │  │
│  │ Verhoeff / PAN / MRZ  │ │ MIME Parser + Triage  │ │ Consent Workflows │  │
│  └───────────────────────┘ └───────────────────────┘ └───────────────────┘  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Async SQLAlchemy 2.0
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                  Relational Storage & Audit Trail                           │
│  • SQLite (Async WAL mode) or PostgreSQL                                    │
│  • 13 Isolated Models: Cases, Applicants, Documents, Fields, Audits, Shares │
│  • Immutable Append-Only Audit Log with SHA-256 integrity                   │
│  • SHA-256 Deduplicated Document Storage (Local disk / Object storage)      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart Guide (Zero-Docker Local Run)

### Prerequisites
- Python 3.10, 3.11, or 3.12
- Node.js 18+ (optional, only needed for modifying frontend source)
- Git

### 1. Clone & Set Up Virtual Environment

```bash
# Clone the repository
git clone https://github.com/VinilJoseph/ckyc_agentic.git
cd ckyc_agentic

# Create and activate Python virtual environment
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate

# Install backend dependencies
pip install -r backend/requirements.txt
```

### 2. Launch the Application Server

Start the asynchronous FastAPI server with auto-reload:

```bash
# From workspace root
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

The application initializes SQLite in WAL mode and mounts the static interactive SPA frontend.

### 3. Open the Interactive Showcase UI

Navigate in your browser to:
- **Interactive Showcase UI**: [http://localhost:8000/](http://localhost:8000/)
- **Swagger / OpenAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc API Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Comprehensive Verification & Test Suite

The test suite contains **286 automated tests** structured into 5 rigorous tiers covering feature parity, boundary and corner cases, cross-feature multi-step integration, real-world onboarding scenarios, and adversarial stress hardening.

### Running Tests

```bash
# Run the entire E2E test suite (All 286 tests across Tiers 1–5)
python -m pytest backend/tests/e2e -v --tb=short

# Run with concise summary
python -m pytest backend/tests/e2e -q

# Run frontend test suite
python -m pytest backend/tests/test_m4_frontend.py -v
```

### Test Hierarchy Breakdown
- **Tier 1 — Feature Coverage (110 tests)**: Exhaustive tests for all 22 project features (F01–F22).
- **Tier 2 — Boundary & Corner Cases (110 tests)**: Extreme inputs, invalid checksums, payload limits, cross-tenant leak attempts, and unauthorized mutations.
- **Tier 3 — Cross-Feature Integration (22 tests)**: End-to-end multi-step flows spanning OCR extraction, validation, reviewer overrides, and sharing grants.
- **Tier 4 — Real-World KYC Scenarios (5 scenarios, 43 sub-stages)**: Standard adult onboarding, minor applicant guardian consent, cross-tenant isolation, high-volume email ingestion, and revocation lifecycle.
- **Tier 5 — Adversarial Stress Testing (39 tests)**: Deep security hardening, state machine bypassing attempts, audit immutability verification, and spoofed document injections.

---

## 📡 Key API Endpoints Reference

All `/api/v1/` endpoints enforce multi-tenancy via the `X-Tenant-ID` header and double-submit CSRF protection for mutating operations.

| Endpoint | Method | Description | Security |
|---|---|---|---|
| `/api/v1/auth/login` | `POST` | Authenticate tenant user and issue JWT cookie | Public |
| `/api/v1/cases` | `GET` | List KYC cases with status, pagination, and search filters | Reviewer / Admin |
| `/api/v1/cases` | `POST` | Create a new KYC case for an applicant | Reviewer / Admin |
| `/api/v1/cases/{id}` | `GET` | Fetch comprehensive case detail (documents, extracted fields, stepper) | Reviewer / Admin |
| `/api/v1/cases/{id}/status` | `PATCH` | Transition case state via the 11-status finite state machine | Reviewer / Admin |
| `/api/v1/cases/{id}/documents` | `POST` | Secure document upload (PDF, PNG, JPEG) with magic-byte check | Reviewer / Admin |
| `/api/v1/cases/{id}/documents/{doc_id}/ocr` | `POST` | Trigger OCR extraction and auto-populate KYC fields | Reviewer / Admin |
| `/api/v1/cases/{id}/validate` | `POST` | Run algorithmic KYC validation (Verhoeff, PAN, MRZ, DL) | Reviewer / Admin |
| `/api/v1/cases/{id}/selfie-match` | `POST` | Execute selfie-to-ID biometric facial similarity matching | Reviewer / Admin |
| `/api/v1/cases/{id}/fields/{field_id}` | `PATCH` | Reviewer field decision control (Accept, Correct, Reject) | Reviewer / Admin |
| `/api/v1/cases/{id}/review/approve` | `POST` | Approve KYC case and transition to `approved` state | Reviewer / Admin |
| `/api/v1/cases/{id}/review/reject` | `POST` | Reject KYC case with mandatory compliance rejection reason | Reviewer / Admin |
| `/api/v1/intake/email` | `POST` | Ingest email payload via REST webhook | Ingestion API |
| `/api/v1/intake/eml` | `POST` | Ingest raw RFC 822 `.eml` file with auto-attachment extraction | Ingestion API |
| `/api/v1/email/exceptions` | `GET` | List unmatched email exception queue | Reviewer / Admin |
| `/api/v1/email/exceptions/{id}/assign` | `POST` | Manually assign unmatched email to target KYC case | Reviewer / Admin |
| `/api/v1/email/exceptions/{id}/dismiss` | `POST` | Dismiss unmatched email exception | Reviewer / Admin |
| `/api/v1/cases/{id}/shares` | `POST` | Create a selective credential share grant with expiry | Reviewer / Admin |
| `/api/v1/shares/{token}/consent` | `POST` | Applicant consent submission for credential sharing | Applicant / Public |
| `/api/v1/shares/{token}/access` | `GET` | Verified claim consumption by external requesting institution | Token Auth |
| `/api/v1/shares/{id}/revoke` | `POST` | Immediately revoke an active credential share grant | Reviewer / Admin |
| `/api/v1/cases/{id}/audit-trail` | `GET` | Retrieve chronological, immutable audit trail for case | Compliance Auditor |
| `/api/v1/tenants/usage` | `GET` | Query usage quotas, cases created, and documents uploaded | Tenant Admin |
| `/api/v1/users/me/preferences` | `GET`/`PATCH` | Retrieve or persist user theme preferences (`dark`/`light`) | Authenticated User |

---

## 🖥️ Showcase UI Walkthrough

The web SPA showcases real-time KYC operations with an intuitive UI:

1. **Dual-Theme Design System**:
   - **Obsidian Dark**: High-contrast, dark-mode terminal inspired by modern developer and security consoles.
   - **Fintech Light**: Clean, modern financial-institution design with crisp typography and subtle borders.
   - Instant toggle with persistence in user profile.
2. **Reviewer Workspace (55/45 Split View)**:
   - **Left Panel (55%)**: High-fidelity document viewer with support for multi-page PDFs, high-res images, pan/zoom, and thumbnail navigation.
   - **Right Panel (45%)**: Extracted fields deck with confidence badges, validation issue chips, and original draft vs. corrected values.
3. **Field Decision Deck**:
   - Inline decision controls on every extracted field (`Accept`, `Correct`, `Reject`).
   - Audit trail records who made each change, original OCR value, corrected value, and timestamp.
4. **Sticky Decision Bar**:
   - Bottom docking bar tracking overall decision status.
   - Fast action buttons: `Approve Case`, `Request Clarification`, or `Reject Case` with modal reason input.
5. **Email Simulator Modal**:
   - Allows stakeholders to simulate inbound customer emails with attached identity cards.
   - Automatically demonstrates token parsing (`[CASE-0001]`), case linking, or routing to the Exception Queue.
6. **Credential Sharing Showcase**:
   - Configure selective field sharing (e.g., share Full Name and Date of Birth while masking Tax ID).
   - Demonstrates consent token generation, applicant confirmation flow, and one-time access verification.

---

## 🌿 Git Branching & Milestone Release Model

The project adheres to a clean, enterprise Git branching architecture with granular, atomic Conventional Commits:

### Branch Topology
- `master`: Production release branch.
- `feat-dev1`: Active integration and development branch.
- `feature/m1-core-architecture`: Core scaffolding, SQLite async DB, 13 SQLAlchemy models, 11-status state machine, JWT+CSRF auth.
- `feature/m2-document-ocr-pipeline`: Local storage, multi-tier OCR engine, algorithmic KYC validation, selfie biometric matcher.
- `feature/m3-email-intake-biometrics`: RFC 822 & MIME email parser, background ingestion, exception queue triage.
- `feature/m4-interactive-showcase-ui`: Dual-theme design system, 55/45 Reviewer Workspace, applicant portal, email simulator modal.
- `feature/m5-e2e-integration-acceptance`: Synthetic test harness, 286 E2E integration tests (Tiers 1–5), production standards, and README.

### Milestone Release Tags
- `v0.1.0-alpha.m1`: Milestone 1 — Core Architecture & Security Foundation
- `v0.2.0-alpha.m2`: Milestone 2 — Document OCR Pipeline & Algorithmic Validation
- `v0.3.0-alpha.m3`: Milestone 3 — Email Intake & Exception Queue Management
- `v0.4.0-alpha.m4`: Milestone 4 — Interactive Reviewer Workspace & Showcase UI
- `v1.0.0-mvp`: Milestone 5 — Full E2E Integration, Hardening & Acceptance Release

---

## 🛡️ Security & Privacy Compliance

- **Tenant Isolation**: Every database query is scoped by `tenant_id`. Cross-tenant queries return HTTP 404 to avoid leaking tenant existence.
- **CSRF Defense**: Double-submit cookie with cryptographic token verification on all state-changing HTTP requests.
- **PII Protection**: Identity documents are hashed with SHA-256 and stored with sanitized filenames. Raw document bytes and sensitive secrets are never logged in plain text.
- **Append-Only Audit**: All lifecycle operations, field corrections, and reviewer decisions are committed to an immutable append-only audit trail.

---

## 📄 License
This project is proprietary and confidential. Built as a capability showcase MVP for CKYC/eKYC marketplace demonstration.
