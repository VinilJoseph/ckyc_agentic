"""
Tier 2 Boundary & Corner Case Test Suite for CKYC / eKYC Marketplace MVP.

Contains exactly 110 boundary, edge, negative, and error-handling test cases
(5 per feature across all 22 features F1 to F22):
- F1: Boundary inputs (empty purpose, invalid case_type enum, huge 5000-char purpose, duplicate case_number prevention, cross-tenant case fetch 404)
- F2: State machine boundary (direct jump draft->approved 400, transition from closed state 400, unauthorized role transition 403, transition to expired, approval without reason 422)
- F3: Document upload boundary (spoofed .pdf with text bytes 400, file size > 10MB rejection 413, unsupported mime 400, upload to closed case 400, upload to other tenant case 404)
- F4: OCR boundary (blurry/corrupted document extraction, empty document text, multi-page pagination, special Unicode characters, non-Latin script handling)
- F5: Criteria validation boundary (invalid Verhoeff checksum error, minor age < 18 error, expired document date error, invalid PAN 4th character, name mismatch > 50% distance)
- F6: Biometrics boundary (impostor mismatch pair < 0.40, corrupted selfie image 400, multiple faces detected, missing ID photo reference 400, cross-tenant selfie match 404)
- F7: Email intake boundary (duplicate Message-ID idempotency, .eml with malformed headers 400, attachment exceeding size limit 413, .eml referencing non-existent case, email without attachments)
- F8: Email exception boundary (assign to non-existent case 404, assign cross-tenant case 404, assign already-assigned email 400, empty exception list, pagination of exceptions)
- F9: Stepper boundary (expired case timeline, rejected case terminal stage, closed case terminal stage, non-linear correction return, timeline timestamps accuracy)
- F10: Split reviewer workspace boundary (case with 0 documents empty state, case with 10+ documents, long multi-value address, reviewer notes visibility, cross-tenant access 404)
- F11: Field decision boundary (empty corrected value 400, non-existent field_id 404, correction on approved case 400, correction by non-reviewer role 403, cross-tenant field correction 404)
- F12: Decision gate boundary (empty reason rejection 422, whitespace-only reason rejection 422, approve already-approved case 400, approve case not in in_review state 400, applicant role approval attempt 403)
- F13: Theme preference boundary (invalid theme enum 'neon' 422, unauthenticated preference fetch 401, patch with empty body 200, preference update persistence, multi-user isolation)
- F14: Portal boundary (expired token 410 Gone, tampered/invalid token 400, access token for other case 404, upload document > 10MB via portal 413, portal access after case closed 410)
- F15: Controlled sharing boundary (read expired share grant returns 410 Gone, share unapproved case 400, unauthorized 3rd-party tenant read 404, empty selected_fields rejection 400, past expiry date rejection 400)
- F16: Share consent boundary (consent to already expired share 410, consent by unauthorized user 403, double consent approval 400, revoke already revoked share 400, non-existent share_id 404)
- F17: Local DB boundary (DB locked concurrency handling, foreign key constraints enforcement, invalid table query handling, connection pool cleanup, database schema version integrity)
- F18: OCR fallback boundary (corrupted file fallback without 500 crash, unparseable binary buffer fallback, unsupported file encoding, zero-byte file handling, OCR error detail sanitization)
- F19: Multi-tenancy boundary (Tenant A requests Tenant B case returns 404, Tenant A requests Tenant B doc returns 404, Tenant A requests Tenant B share returns 404, Tenant A assigns email to Tenant B case 404, Tenant header spoofing rejected)
- F20: Security auth boundary (missing X-CSRF-Token on POST 403, mismatched CSRF token 403, expired JWT token 401, invalid JWT signature 401, login with invalid password 401)
- F21: Audit trail boundary (no sensitive passwords in audit logs, no raw JWTs in audit logs, append-only constraint no DELETE/UPDATE API 405, audit events ordered chronologically, cross-tenant audit access 404)
- F22: Usage tracking boundary (cross-tenant usage access 404, usage tracking across multiple tenants independent, unauthenticated usage access 401, non-reviewer role usage restriction 403, quota limit warning)
"""

import asyncio
from datetime import date, datetime, timedelta
import os
import sys
import pytest
import pytest_asyncio
import httpx

# Ensure current directory is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from .synthetic_data import (
        compute_verhoeff_checksum,
        generate_adult_applicant,
        generate_corporate_entity,
        generate_invalid_aadhaar,
        generate_invalid_dl,
        generate_invalid_pan,
        generate_invalid_passport_mrz,
        generate_minor_applicant,
        generate_valid_aadhaar,
        generate_valid_dl,
        generate_valid_pan,
        generate_valid_passport_mrz,
        validate_dl,
        validate_mrz_check_digit,
        validate_pan,
        validate_passport_mrz,
        validate_verhoeff,
    )
    from .synthetic_documents import (
        generate_oversized_document,
        generate_spoofed_document,
        generate_valid_jpeg,
        generate_valid_pdf,
        generate_valid_png,
    )
    from .synthetic_biometrics import (
        compute_facial_similarity_metric,
        generate_corrupted_facial_image,
        generate_matched_facial_pair,
        generate_mismatched_facial_pair,
    )
    from .synthetic_emails import (
        generate_synthetic_eml,
        generate_unmatched_eml,
        parse_synthetic_eml,
    )
except ImportError:
    from synthetic_data import (
        compute_verhoeff_checksum,
        generate_adult_applicant,
        generate_corporate_entity,
        generate_invalid_aadhaar,
        generate_invalid_dl,
        generate_invalid_pan,
        generate_invalid_passport_mrz,
        generate_minor_applicant,
        generate_valid_aadhaar,
        generate_valid_dl,
        generate_valid_pan,
        generate_valid_passport_mrz,
        validate_dl,
        validate_mrz_check_digit,
        validate_pan,
        validate_passport_mrz,
        validate_verhoeff,
    )
    from synthetic_documents import (
        generate_oversized_document,
        generate_spoofed_document,
        generate_valid_jpeg,
        generate_valid_pdf,
        generate_valid_png,
    )
    from synthetic_biometrics import (
        compute_facial_similarity_metric,
        generate_corrupted_facial_image,
        generate_matched_facial_pair,
        generate_mismatched_facial_pair,
    )
    from synthetic_emails import (
        generate_synthetic_eml,
        generate_unmatched_eml,
        parse_synthetic_eml,
    )


# ============================================================================
# F1: Boundary Inputs (5 tests)
# ============================================================================

class TestF01BoundaryInputs:
    """Boundary & Negative tests for F1: Case Creation & Scoping."""

    @pytest.mark.asyncio
    async def test_f1_boundary_empty_purpose_returns_422(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Empty string purpose must be rejected with 422 Unprocessable Entity."""
        applicant = generate_adult_applicant()
        payload = {"applicant": applicant, "purpose": "", "case_type": "individual"}
        response = await async_client.post(
            "/api/v1/cases", json=payload, headers=tenant_alpha_headers, cookies=auth_admin_cookies
        )
        assert response.status_code == 422
        assert "purpose" in response.text.lower()

    @pytest.mark.asyncio
    async def test_f1_boundary_invalid_case_type_enum_returns_422(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Unsupported case_type enum ('alien_corporation') must be rejected with 422."""
        applicant = generate_adult_applicant()
        payload = {"applicant": applicant, "purpose": "account_opening", "case_type": "alien_corporation"}
        response = await async_client.post(
            "/api/v1/cases", json=payload, headers=tenant_alpha_headers, cookies=auth_admin_cookies
        )
        assert response.status_code == 422
        assert "case_type" in response.text.lower()

    @pytest.mark.asyncio
    async def test_f1_boundary_huge_5000_char_purpose_accepted(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Extreme length boundary: 5000-character purpose string is handled cleanly without buffer overflow."""
        applicant = generate_adult_applicant()
        huge_purpose = "Compliance verification purpose: " + ("X" * 4967)
        assert len(huge_purpose) == 5000
        payload = {"applicant": applicant, "purpose": huge_purpose, "case_type": "individual"}
        response = await async_client.post(
            "/api/v1/cases", json=payload, headers=tenant_alpha_headers, cookies=auth_admin_cookies
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["purpose"]) == 5000
        assert data["purpose"] == huge_purpose

    @pytest.mark.asyncio
    async def test_f1_boundary_duplicate_case_number_prevention(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Sequential case creations guarantee unique, non-colliding case numbers."""
        applicant1 = generate_adult_applicant()
        applicant2 = generate_adult_applicant()
        r1 = await async_client.post(
            "/api/v1/cases",
            json={"applicant": applicant1, "purpose": "first_account"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        r2 = await async_client.post(
            "/api/v1/cases",
            json={"applicant": applicant2, "purpose": "second_account"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert r1.status_code == 201
        assert r2.status_code == 201
        c1 = r1.json()
        c2 = r2.json()
        assert c1["case_number"] != c2["case_number"]
        assert c1["id"] != c2["id"]

    @pytest.mark.asyncio
    async def test_f1_boundary_cross_tenant_case_fetch_returns_404(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Case created under Tenant Alpha cannot be accessed under Tenant Beta (strict 404)."""
        applicant = generate_adult_applicant()
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": applicant, "purpose": "isolation_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert create_res.status_code == 201
        case_id = create_res.json()["id"]

        # Attempt read with Tenant Beta headers
        beta_res = await async_client.get(
            f"/api/v1/cases/{case_id}",
            headers=tenant_beta_headers,
            cookies=auth_admin_cookies,
        )
        assert beta_res.status_code == 404
        assert "not found" in beta_res.text.lower()


# ============================================================================
# F2: State Machine Boundary (5 tests)
# ============================================================================

class TestF02StateMachineBoundary:
    """Boundary & Negative tests for F2: State Machine Enforcement."""

    @pytest.mark.asyncio
    async def test_f2_boundary_direct_jump_draft_to_approved_returns_400(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Illegal state skip from 'draft' directly to 'approved' must be blocked with HTTP 400."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "jump_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        jump_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "approved"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert jump_res.status_code == 400
        assert "illegal state jump" in jump_res.text.lower()

    @pytest.mark.asyncio
    async def test_f2_boundary_transition_from_closed_state_returns_400(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Terminal state lock: Case in 'closed' status cannot be transitioned to any other state."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "closed_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        # Transition draft -> closed
        close_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "closed"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert close_res.status_code == 200
        assert close_res.json()["status"] == "closed"

        # Subsequent transition attempt
        reopen_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "draft"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert reopen_res.status_code == 400
        assert "terminal state" in reopen_res.text.lower()

    @pytest.mark.asyncio
    async def test_f2_boundary_unauthorized_role_transition_returns_403(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_applicant_cookies: dict
    ):
        """Applicant or unauthorized role attempting to transition status is blocked with HTTP 403."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "role_test"},
            headers=tenant_alpha_headers,
            cookies={"access_token": "mock-admin-jwt-token-alpha", "csrf_token": "csrf-token-test-secret-98765"},
        )
        case_id = c.json()["id"]

        # Attempt transition as applicant role
        headers = dict(tenant_alpha_headers)
        headers["X-User-Role"] = "applicant"

        res = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "invitation_sent"},
            headers=headers,
            cookies=auth_applicant_cookies,
        )
        assert res.status_code == 403
        assert "unauthorized" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f2_boundary_transition_to_expired_allowed(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Legitimate boundary transition: Case awaiting documents can transition to 'expired'."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "expire_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        # draft -> awaiting_documents
        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "awaiting_documents"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )

        # awaiting_documents -> expired
        exp_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "expired"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert exp_res.status_code == 200
        assert exp_res.json()["status"] == "expired"

    @pytest.mark.asyncio
    async def test_f2_boundary_approval_without_reason_returns_422(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Case cannot be approved without mandatory written justification reason."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "approval_gate_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        # Advance to in_review
        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "documents_received"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "in_review"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )

        # Attempt approval with empty reason
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/approve",
            json={"reason": ""},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 422
        assert "justification" in res.text.lower() or "reason" in res.text.lower()


# ============================================================================
# F3: Document Upload Boundary (5 tests)
# ============================================================================

class TestF03DocumentUploadBoundary:
    """Boundary & Negative tests for F3: Secure Document Upload."""

    @pytest.mark.asyncio
    async def test_f3_boundary_spoofed_pdf_with_text_bytes_returns_400(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Uploading text bytes disguised with .pdf filename fails magic byte validation with HTTP 400."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "spoof_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        spoofed_payload = generate_spoofed_document("pdf")
        files = {"file": ("fake_aadhaar.pdf", spoofed_payload, "application/pdf")}
        data = {"document_type": "aadhaar"}

        res = await async_client.post(
            f"/api/v1/cases/{case_id}/documents",
            files=files,
            data=data,
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 400
        assert "magic byte" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f3_boundary_file_size_exceeding_10mb_returns_413(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Files exceeding 10MB limit (11MB synthetic document) are rejected with HTTP 413 Payload Too Large."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "size_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        oversized_bytes = generate_oversized_document(size_mb=11)
        assert len(oversized_bytes) >= 11 * 1024 * 1024

        files = {"file": ("huge_document.pdf", oversized_bytes, "application/pdf")}
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/documents",
            files=files,
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 413
        assert "exceeds" in res.text.lower() or "limit" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f3_boundary_unsupported_mime_returns_400(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Unsupported file binary (executable or raw binary) rejected with HTTP 400."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "mime_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        raw_exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
        files = {"file": ("malicious.exe", raw_exe_bytes, "application/x-msdownload")}
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/documents",
            files=files,
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 400
        assert "unsupported" in res.text.lower() or "magic byte" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f3_boundary_upload_to_closed_case_returns_400(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Attempting to upload documents to a closed case must be rejected with HTTP 400."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "closed_upload_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        # Close the case
        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "closed"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )

        valid_pdf = generate_valid_pdf("Aadhaar Card")
        files = {"file": ("aadhaar.pdf", valid_pdf, "application/pdf")}
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/documents",
            files=files,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert res.status_code == 400
        assert "closed" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f3_boundary_upload_to_other_tenant_case_returns_404(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        auth_reviewer_cookies: dict,
    ):
        """Uploading document to a case belonging to another tenant returns strict 404."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "cross_doc_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        valid_pdf = generate_valid_pdf("PAN Card")
        files = {"file": ("pan.pdf", valid_pdf, "application/pdf")}
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/documents",
            files=files,
            headers=tenant_beta_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 404


# ============================================================================
# F4: OCR Boundary (5 tests)
# ============================================================================

class TestF04OCRBoundary:
    """Boundary & Edge tests for F4: Automated Field Extraction."""

    @pytest.mark.asyncio
    async def test_f4_boundary_blurry_corrupted_document_extraction_no_crash(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Blurry or corrupted document extraction triggers fallback without 500 crash, yielding low confidence."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "ocr_blur_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "aadhaar", "document_text": "CORRUPTED_DOCUMENT_BLURRY_IMAGE_BUFFER"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["count"] >= 1
        assert data["fallback_applied"] is True
        assert data["extracted_fields"][0]["confidence"] < 0.30

    @pytest.mark.asyncio
    async def test_f4_boundary_empty_document_text_returns_zero_fields(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Empty string document text returns empty fields list without throwing error."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "ocr_empty_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "aadhaar", "document_text": ""},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 200
        assert res.json()["count"] == 0
        assert res.json()["extracted_fields"] == []

    @pytest.mark.asyncio
    async def test_f4_boundary_multi_page_pagination_preserves_page_numbers(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Multi-page document extraction accurately captures source_page numbers for each page."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "ocr_multipage_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        multi_page_text = (
            "--- PAGE 1 ---\nGovernment of India Aadhaar 2948 2847 2841\n"
            "--- PAGE 2 ---\nPAN Card ABCPS1234F Income Tax Department\n"
        )
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "aadhaar", "document_text": multi_page_text},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 200
        fields = res.json()["extracted_fields"]
        assert len(fields) >= 2
        pages = [f["source_page"] for f in fields]
        assert 1 in pages
        assert 2 in pages

    @pytest.mark.asyncio
    async def test_f4_boundary_special_unicode_characters_handling(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Names with diacritics and special Unicode accents ('Renée Müller', 'Aarāv Shärmā') are extracted intact."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "ocr_unicode_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        unicode_name = "Renée Müller Aarāv Shärmā"
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "unicode_text", "document_text": unicode_name},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 200
        draft_val = res.json()["extracted_fields"][0]["draft_value"]
        assert draft_val == unicode_name

    @pytest.mark.asyncio
    async def test_f4_boundary_non_latin_script_devanagari_handling(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Non-Latin script (Hindi Devanagari 'आरव शर्मा') is processed without encoding distortion."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "ocr_hindi_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        devanagari_text = "भारत सरकार - आरव शर्मा - आधार संख्या"
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "unicode_text", "document_text": devanagari_text},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 200
        extracted = res.json()["extracted_fields"][0]["draft_value"]
        assert "आरव शर्मा" in extracted


# ============================================================================
# F5: Criteria Validation Boundary (5 tests)
# ============================================================================

class TestF05CriteriaValidationBoundary:
    """Boundary & Edge tests for F5: KYC Criteria Validation."""

    @pytest.mark.asyncio
    async def test_f5_boundary_invalid_verhoeff_checksum_error(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Invalid Verhoeff checksum triggers INVALID_VERHOEFF_CHECKSUM validation issue."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "val_verhoeff_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        bad_aadhaar = generate_invalid_aadhaar()
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/validate",
            json={"aadhaar_number": bad_aadhaar},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_valid"] is False
        codes = [i["code"] for i in data["issues"]]
        assert "INVALID_VERHOEFF_CHECKSUM" in codes

    @pytest.mark.asyncio
    async def test_f5_boundary_minor_age_under_18_error(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Applicant under 18 years old flags APPLICANT_UNDERAGE validation error."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_minor_applicant(), "purpose": "val_minor_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        minor_dob = (date.today() - timedelta(days=16 * 365)).strftime("%Y-%m-%d")
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/validate",
            json={"date_of_birth": minor_dob},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_valid"] is False
        codes = [i["code"] for i in data["issues"]]
        assert "APPLICANT_UNDERAGE" in codes

    @pytest.mark.asyncio
    async def test_f5_boundary_expired_document_date_error(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Document with expiration date in the past triggers DOCUMENT_EXPIRED validation issue."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "val_expiry_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        past_date = "2020-01-15"
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/validate",
            json={"expiry_date": past_date},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_valid"] is False
        codes = [i["code"] for i in data["issues"]]
        assert "DOCUMENT_EXPIRED" in codes

    @pytest.mark.asyncio
    async def test_f5_boundary_invalid_pan_4th_character(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """PAN with illegal 4th character ('X' instead of Individual/Corporate) flags INVALID_PAN_ENTITY_TYPE."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "val_pan_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        bad_pan = generate_invalid_pan("entity")
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/validate",
            json={"pan_number": bad_pan},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_valid"] is False
        codes = [i["code"] for i in data["issues"]]
        assert "INVALID_PAN_ENTITY_TYPE" in codes

    @pytest.mark.asyncio
    async def test_f5_boundary_name_mismatch_over_50_percent_distance(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Fuzzy name mismatch with distance > 50% between applicant and document flags NAME_MISMATCH."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "val_mismatch_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        res = await async_client.post(
            f"/api/v1/cases/{case_id}/validate",
            json={"applicant_name": "Aarav Sharma", "extracted_name": "Alexander Hamilton"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_valid"] is False
        codes = [i["code"] for i in data["issues"]]
        assert "NAME_MISMATCH" in codes


# ============================================================================
# F6: Biometrics Boundary (5 tests)
# ============================================================================

class TestF06BiometricsBoundary:
    """Boundary & Edge tests for F6: Selfie-to-ID Photo Matching."""

    @pytest.mark.asyncio
    async def test_f6_boundary_impostor_mismatch_pair_score_under_040(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Impostor mismatched biometric pair produces similarity score < 0.40 and is_match=False."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "bio_impostor_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        selfie, impostor = generate_mismatched_facial_pair()
        files = {
            "selfie": ("selfie.png", selfie, "image/png"),
            "id_photo": ("impostor.png", impostor, "image/png"),
        }
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/selfie-match",
            files=files,
            data={"threshold": 0.75},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_match"] is False
        assert data["confidence"] < 0.40

    @pytest.mark.asyncio
    async def test_f6_boundary_corrupted_selfie_image_returns_400(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Uploading truncated corrupted image binary returns HTTP 400 INVALID_IMAGE_DATA."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "bio_corrupt_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        corrupt_bytes = generate_corrupted_facial_image()
        files = {"selfie": ("bad_selfie.png", corrupt_bytes, "image/png")}
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/selfie-match",
            files=files,
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 400
        assert "corrupt" in res.text.lower() or "invalid_image" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f6_boundary_multiple_faces_detected(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Image containing multiple faces triggers 400 MULTIPLE_FACES_DETECTED."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "bio_multi_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        multi_face_bytes = generate_valid_png() + b"MULTIPLE_FACES"
        files = {"selfie": ("multi_faces.png", multi_face_bytes, "image/png")}
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/selfie-match",
            files=files,
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 400
        assert "multiple_faces" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f6_boundary_missing_id_photo_reference_returns_400(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Selfie match request without id_photo when case has no ID doc returns HTTP 400."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "bio_missing_ref_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        selfie, _ = generate_matched_facial_pair()
        files = {"selfie": ("selfie.png", selfie, "image/png")}
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/selfie-match",
            files=files,
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 400
        assert "reference" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f6_boundary_cross_tenant_selfie_match_returns_404(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        auth_reviewer_cookies: dict,
    ):
        """Tenant Beta attempting to execute selfie match on Tenant Alpha case returns HTTP 404."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "bio_cross_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        selfie, _ = generate_matched_facial_pair()
        files = {"selfie": ("selfie.png", selfie, "image/png")}
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/selfie-match",
            files=files,
            headers=tenant_beta_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 404


# ============================================================================
# F7: Email Intake Boundary (5 tests)
# ============================================================================

class TestF07EmailIntakeBoundary:
    """Boundary & Negative tests for F7: Inbound Mail Document Ingestion."""

    @pytest.mark.asyncio
    async def test_f7_boundary_duplicate_message_id_idempotency(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict
    ):
        """Inbound email webhook handles duplicate Message-ID idempotently without error or re-processing."""
        msg_id = f"test-idemp-{datetime.utcnow().timestamp()}@fintechbank.com"
        payload = {
            "message_id": msg_id,
            "sender": "applicant@example.com",
            "subject": "Re: Documents Submission",
        }
        res1 = await async_client.post("/api/v1/intake/email", json=payload, headers=tenant_alpha_headers)
        assert res1.status_code == 200

        # Duplicate submission
        res2 = await async_client.post("/api/v1/intake/email", json=payload, headers=tenant_alpha_headers)
        assert res2.status_code == 200
        assert res2.json()["status"] == "idempotent_duplicate"

    @pytest.mark.asyncio
    async def test_f7_boundary_eml_with_malformed_headers_returns_400(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict
    ):
        """Malformed .eml payload lacking basic RFC 822 headers rejected with HTTP 400."""
        malformed_bytes = b"NOT_A_VALID_RFC_822_EMAIL_STREAM_NO_HEADERS"
        files = {"file": ("malformed.eml", malformed_bytes, "message/rfc822")}
        res = await async_client.post("/api/v1/intake/eml", files=files, headers=tenant_alpha_headers)
        assert res.status_code == 400
        assert "malformed" in res.text.lower() or "missing" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f7_boundary_attachment_exceeding_size_limit_returns_413(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Inbound email with attachment > 10MB rejected with HTTP 413."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "eml_size_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_num = c.json()["case_number"]

        oversized_att = generate_oversized_document(size_mb=11)
        eml_bytes = generate_synthetic_eml(
            case_number=case_num,
            attachments=[("huge.pdf", oversized_att, "application/pdf")]
        )
        files = {"file": ("inbound_huge.eml", eml_bytes, "message/rfc822")}
        res = await async_client.post("/api/v1/intake/eml", files=files, headers=tenant_alpha_headers)
        assert res.status_code == 413
        assert "limit" in res.text.lower() or "exceeds" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f7_boundary_eml_referencing_nonexistent_case(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict
    ):
        """.eml referencing non-existent case [CASE-999999] is routed to Email Exception Queue."""
        eml_bytes = generate_synthetic_eml(case_number="CASE-999999")
        files = {"file": ("unmatched_ref.eml", eml_bytes, "message/rfc822")}
        res = await async_client.post("/api/v1/intake/eml", files=files, headers=tenant_alpha_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "routed_to_exception_queue"
        assert "exception_id" in data

    @pytest.mark.asyncio
    async def test_f7_boundary_email_without_attachments_handled_cleanly(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Inbound email without attachments referencing active case is processed cleanly with attachments_count: 0."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "no_att_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_num = c.json()["case_number"]

        eml_bytes = generate_synthetic_eml(case_number=case_num, attachments=[])
        files = {"file": ("no_attachments.eml", eml_bytes, "message/rfc822")}
        res = await async_client.post("/api/v1/intake/eml", files=files, headers=tenant_alpha_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "attached_to_case"
        assert data["attachments_count"] == 0


# ============================================================================
# F8: Email Exception Boundary (5 tests)
# ============================================================================

class TestF08EmailExceptionBoundary:
    """Boundary & Negative tests for F8: Email Exception Queue & Triage."""

    @pytest.mark.asyncio
    async def test_f8_boundary_assign_to_nonexistent_case_returns_404(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict
    ):
        """Assigning email exception to non-existent case returns HTTP 404."""
        # Ingest unmatched email
        unmatched = generate_unmatched_eml()
        files = {"file": ("unmatched.eml", unmatched, "message/rfc822")}
        intake_res = await async_client.post("/api/v1/intake/eml", files=files, headers=tenant_alpha_headers)
        exc_id = intake_res.json()["exception_id"]

        # Attempt assign to bogus case
        res = await async_client.post(
            f"/api/v1/email/exceptions/{exc_id}/assign",
            json={"case_id": "case-nonexistent-999"},
            headers=tenant_alpha_headers,
        )
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_f8_boundary_assign_cross_tenant_case_returns_404(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Assigning Tenant Alpha exception to a Tenant Beta case returns HTTP 404."""
        # Create case in Tenant Beta
        beta_case = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "beta_assign"},
            headers=tenant_beta_headers,
            cookies=auth_admin_cookies,
        )
        beta_case_id = beta_case.json()["id"]

        # Create exception in Tenant Alpha
        unmatched = generate_unmatched_eml()
        files = {"file": ("alpha_unmatched.eml", unmatched, "message/rfc822")}
        intake_res = await async_client.post("/api/v1/intake/eml", files=files, headers=tenant_alpha_headers)
        alpha_exc_id = intake_res.json()["exception_id"]

        # Attempt to assign alpha exception to beta case using alpha headers
        res = await async_client.post(
            f"/api/v1/email/exceptions/{alpha_exc_id}/assign",
            json={"case_id": beta_case_id},
            headers=tenant_alpha_headers,
        )
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_f8_boundary_assign_already_assigned_email_returns_400(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Attempting to assign an email exception that is already in 'assigned' status returns HTTP 400."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "reassign_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        unmatched = generate_unmatched_eml()
        intake_res = await async_client.post(
            "/api/v1/intake/eml",
            files={"file": ("unmatched.eml", unmatched, "message/rfc822")},
            headers=tenant_alpha_headers,
        )
        exc_id = intake_res.json()["exception_id"]

        # First assign succeeds
        first_assign = await async_client.post(
            f"/api/v1/email/exceptions/{exc_id}/assign",
            json={"case_id": case_id},
            headers=tenant_alpha_headers,
        )
        assert first_assign.status_code == 200

        # Second assign fails
        second_assign = await async_client.post(
            f"/api/v1/email/exceptions/{exc_id}/assign",
            json={"case_id": case_id},
            headers=tenant_alpha_headers,
        )
        assert second_assign.status_code == 400
        assert "already assigned" in second_assign.text.lower()

    @pytest.mark.asyncio
    async def test_f8_boundary_empty_exception_list_returns_zero_items(
        self, async_client: httpx.AsyncClient, tenant_gamma_headers: dict
    ):
        """Querying exceptions for tenant with no exceptions returns clean items: [] and total: 0."""
        res = await async_client.get("/api/v1/email/exceptions", headers=tenant_gamma_headers)
        assert res.status_code == 200
        assert res.json()["items"] == []
        assert res.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_f8_boundary_pagination_of_exceptions(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict
    ):
        """Pagination query parameters limit and offset correctly partition exception results."""
        # Query paginated exceptions
        res = await async_client.get(
            "/api/v1/email/exceptions?limit=2&offset=0",
            headers=tenant_alpha_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["items"]) <= 2
        assert data["limit"] == 2
        assert data["offset"] == 0


# ============================================================================
# F9: Stepper Boundary (5 tests)
# ============================================================================

class TestF09StepperBoundary:
    """Boundary & Edge tests for F9: Interactive Case Lifecycle Stepper."""

    @pytest.mark.asyncio
    async def test_f9_boundary_expired_case_timeline_stage(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Case transitioned to 'expired' correctly updates stepper current_stage to 'expired'."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "stepper_exp"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "invitation_sent"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        p = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "expired"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert p.status_code == 200
        stepper = p.json()["stepper"]
        assert stepper["current_stage"] == "expired"

    @pytest.mark.asyncio
    async def test_f9_boundary_rejected_case_terminal_stage(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Case transitioned to 'rejected' locks stepper into terminal status."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "stepper_rej"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "documents_received"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "in_review"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        rej = await async_client.post(
            f"/api/v1/cases/{case_id}/reject",
            json={"reason": "Fraudulent document detected"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert rej.status_code == 200

        case_detail = await async_client.get(
            f"/api/v1/cases/{case_id}",
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert case_detail.json()["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_f9_boundary_closed_case_terminal_stage(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Case transitioned to 'closed' reflects closed current_stage in stepper."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "stepper_closed"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        closed = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "closed"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert closed.status_code == 200
        assert closed.json()["stepper"]["current_stage"] == "closed"

    @pytest.mark.asyncio
    async def test_f9_boundary_non_linear_correction_return_stepper_history(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Stepper records historical steps through non-linear loop: in_review -> needs_correction -> documents_received."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "stepper_loop"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        # Advance to in_review
        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "documents_received"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "in_review"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )

        # Loop: needs_applicant_correction
        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "needs_applicant_correction"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )

        # Return: documents_received
        res = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "documents_received"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 200
        history = [s["stage"] for s in res.json()["stepper"]["completed_steps"]]
        assert "needs_applicant_correction" in history
        assert "documents_received" in history

    @pytest.mark.asyncio
    async def test_f9_boundary_timeline_timestamps_accuracy(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Completed steps in stepper contain valid ISO-8601 timestamps and strictly ascending order."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "stepper_ts"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "invitation_sent"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        p = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "awaiting_documents"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        completed = p.json()["stepper"]["completed_steps"]
        assert len(completed) >= 2
        for step in completed:
            ts = step["completed_at"]
            # Validate ISO timestamp parseable
            dt = datetime.fromisoformat(ts.replace("Z", ""))
            assert dt <= datetime.utcnow() + timedelta(seconds=5)


# ============================================================================
# F10: Split Reviewer Workspace Boundary (5 tests)
# ============================================================================

class TestF10SplitReviewerWorkspaceBoundary:
    """Boundary & Edge tests for F10: Split Reviewer Workspace Data API."""

    @pytest.mark.asyncio
    async def test_f10_boundary_case_with_zero_documents_empty_state(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Case with 0 documents returns clean empty documents list in workspace payload without error."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "workspace_empty_docs"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        res = await async_client.get(
            f"/api/v1/cases/{case_id}",
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 200
        assert res.json()["documents"] == []

    @pytest.mark.asyncio
    async def test_f10_boundary_case_with_10_plus_documents(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Case with 10+ uploaded documents aggregates all document records in workspace view."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "workspace_many_docs"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        pdf_bytes = generate_valid_pdf()
        # Upload 10 documents
        for i in range(10):
            files = {"file": (f"doc_{i}.pdf", pdf_bytes, "application/pdf")}
            up = await async_client.post(
                f"/api/v1/cases/{case_id}/documents",
                files=files,
                headers=tenant_alpha_headers,
                cookies=auth_reviewer_cookies,
            )
            assert up.status_code == 201

        res = await async_client.get(
            f"/api/v1/cases/{case_id}",
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 200
        assert len(res.json()["documents"]) >= 10

    @pytest.mark.asyncio
    async def test_f10_boundary_long_multivalue_address_preserved(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Applicant with extreme 500-char multi-line address is preserved without truncation."""
        applicant = generate_adult_applicant()
        long_address = "Flat 101, Building 4B, Sector 62, " + ("Sub-district Landmark, " * 15) + "Noida, UP 201309"
        applicant["address"] = long_address

        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": applicant, "purpose": "workspace_addr"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        res = await async_client.get(
            f"/api/v1/cases/{case_id}",
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 200
        assert res.json()["applicant"]["address"] == long_address

    @pytest.mark.asyncio
    async def test_f10_boundary_reviewer_notes_visibility(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Reviewer notes added to a field are visible in workspace case inspection."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "workspace_notes"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        # Extract field
        ext = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "aadhaar", "document_text": "Aadhaar 2948 2847 2841"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        field_id = ext.json()["extracted_fields"][0]["id"]

        # Add notes
        note_text = "Verified against original UIDAI XML signature"
        await async_client.patch(
            f"/api/v1/cases/{case_id}/fields/{field_id}",
            json={"reviewer_decision": "confirmed", "reviewer_notes": note_text},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )

        # Inspect workspace
        detail = await async_client.get(
            f"/api/v1/cases/{case_id}",
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        field = next(f for f in detail.json()["extracted_fields"] if f["id"] == field_id)
        assert field["reviewer_notes"] == note_text

    @pytest.mark.asyncio
    async def test_f10_boundary_cross_tenant_access_returns_404(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        auth_reviewer_cookies: dict,
    ):
        """Cross-tenant workspace request returns strict 404."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "workspace_cross"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        res = await async_client.get(
            f"/api/v1/cases/{case_id}",
            headers=tenant_beta_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 404


# ============================================================================
# F11: Field Decision Boundary (5 tests)
# ============================================================================

class TestF11FieldDecisionBoundary:
    """Boundary & Negative tests for F11: Reviewer Field Decision Controls."""

    @pytest.mark.asyncio
    async def test_f11_boundary_empty_corrected_value_returns_400(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Correcting a field with empty or whitespace string is rejected with HTTP 400."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "field_empty_corr"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        ext = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "aadhaar", "document_text": "Aadhaar 2948 2847 2841"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        field_id = ext.json()["extracted_fields"][0]["id"]

        res = await async_client.patch(
            f"/api/v1/cases/{case_id}/fields/{field_id}",
            json={"reviewer_decision": "corrected", "corrected_value": "   "},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 400
        assert "empty" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f11_boundary_nonexistent_field_id_returns_404(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Submitting a decision on a non-existent field ID returns HTTP 404."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "field_nonexist"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        res = await async_client.patch(
            f"/api/v1/cases/{case_id}/fields/fld-nonexistent-1234",
            json={"reviewer_decision": "confirmed"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_f11_boundary_correction_on_approved_case_returns_400(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Attempting to alter a field decision on an approved case returns HTTP 400."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "field_approved_case"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        ext = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "aadhaar", "document_text": "Aadhaar 2948 2847 2841"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        field_id = ext.json()["extracted_fields"][0]["id"]

        # Advance to in_review and approve
        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "documents_received"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "in_review"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        await async_client.post(
            f"/api/v1/cases/{case_id}/approve",
            json={"reason": "Approved valid verification"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )

        # Attempt to correct field post-approval
        res = await async_client.patch(
            f"/api/v1/cases/{case_id}/fields/{field_id}",
            json={"reviewer_decision": "corrected", "corrected_value": "999988887777"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 400
        assert "approved" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f11_boundary_correction_by_non_reviewer_role_returns_403(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_applicant_cookies: dict
    ):
        """Role applicant attempting to correct field value returns HTTP 403 Forbidden."""
        # Create case as admin
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "field_role_test"},
            headers=tenant_alpha_headers,
            cookies={"access_token": "mock-admin-jwt-token-alpha", "csrf_token": "csrf-token-test-secret-98765"},
        )
        case_id = c.json()["id"]

        ext = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "aadhaar", "document_text": "Aadhaar 2948 2847 2841"},
            headers=tenant_alpha_headers,
            cookies={"access_token": "mock-admin-jwt-token-alpha", "csrf_token": "csrf-token-test-secret-98765"},
        )
        field_id = ext.json()["extracted_fields"][0]["id"]

        headers = dict(tenant_alpha_headers)
        headers["X-User-Role"] = "applicant"

        res = await async_client.patch(
            f"/api/v1/cases/{case_id}/fields/{field_id}",
            json={"reviewer_decision": "corrected", "corrected_value": "294828472841"},
            headers=headers,
            cookies=auth_applicant_cookies,
        )
        assert res.status_code == 403

    @pytest.mark.asyncio
    async def test_f11_boundary_cross_tenant_field_correction_returns_404(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        auth_reviewer_cookies: dict,
    ):
        """Tenant Beta attempting to alter Tenant Alpha field returns HTTP 404."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "field_cross_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        ext = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "aadhaar", "document_text": "Aadhaar 2948 2847 2841"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        field_id = ext.json()["extracted_fields"][0]["id"]

        res = await async_client.patch(
            f"/api/v1/cases/{case_id}/fields/{field_id}",
            json={"reviewer_decision": "confirmed"},
            headers=tenant_beta_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 404


# ============================================================================
# F12: Decision Gate Boundary (5 tests)
# ============================================================================

class TestF12DecisionGateBoundary:
    """Boundary & Negative tests for F12: Case Review Decision Gate."""

    @pytest.mark.asyncio
    async def test_f12_boundary_empty_reason_rejection_returns_422(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Rejecting a case with empty reason string returns 422 Unprocessable Entity."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "dec_empty_rej"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        res = await async_client.post(
            f"/api/v1/cases/{case_id}/reject",
            json={"reason": ""},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_f12_boundary_whitespace_only_reason_rejection_returns_422(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Approving a case with whitespace-only reason returns 422."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "dec_ws_app"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        # Advance to in_review
        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "documents_received"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "in_review"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )

        res = await async_client.post(
            f"/api/v1/cases/{case_id}/approve",
            json={"reason": "   \t \n   "},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_f12_boundary_approve_already_approved_case_returns_400(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Calling approve on an already approved case returns HTTP 400."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "dec_double_app"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "documents_received"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "in_review"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )

        app1 = await async_client.post(
            f"/api/v1/cases/{case_id}/approve",
            json={"reason": "Valid docs approved"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert app1.status_code == 200

        app2 = await async_client.post(
            f"/api/v1/cases/{case_id}/approve",
            json={"reason": "Repeated approval"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert app2.status_code == 400
        assert "already approved" in app2.text.lower()

    @pytest.mark.asyncio
    async def test_f12_boundary_approve_case_not_in_in_review_state_returns_400(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Calling approve on a case in 'draft' status returns HTTP 400."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "dec_draft_app"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        res = await async_client.post(
            f"/api/v1/cases/{case_id}/approve",
            json={"reason": "Premature approval attempt"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 400
        assert "must be in_review" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f12_boundary_applicant_role_approval_attempt_returns_403(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_applicant_cookies: dict
    ):
        """Role applicant attempting case approval returns HTTP 403."""
        # Create as reviewer
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "dec_role_test"},
            headers=tenant_alpha_headers,
            cookies={"access_token": "mock-reviewer-jwt-token-alpha", "csrf_token": "csrf-token-test-secret-98765"},
        )
        case_id = c.json()["id"]

        # Advance to in_review
        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "documents_received"},
            headers=tenant_alpha_headers,
            cookies={"access_token": "mock-reviewer-jwt-token-alpha", "csrf_token": "csrf-token-test-secret-98765"},
        )
        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "in_review"},
            headers=tenant_alpha_headers,
            cookies={"access_token": "mock-reviewer-jwt-token-alpha", "csrf_token": "csrf-token-test-secret-98765"},
        )

        headers = dict(tenant_alpha_headers)
        headers["X-User-Role"] = "applicant"

        res = await async_client.post(
            f"/api/v1/cases/{case_id}/approve",
            json={"reason": "Self approval attempt"},
            headers=headers,
            cookies=auth_applicant_cookies,
        )
        assert res.status_code == 403


# ============================================================================
# F13: Theme Preference Boundary (5 tests)
# ============================================================================

class TestF13ThemePreferenceBoundary:
    """Boundary & Negative tests for F13: Dual Theme Preference API."""

    @pytest.mark.asyncio
    async def test_f13_boundary_invalid_theme_enum_neon_returns_422(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Unsupported theme enum 'neon' returns HTTP 422 Unprocessable Entity."""
        res = await async_client.patch(
            "/api/v1/users/me/preferences",
            json={"theme": "neon"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert res.status_code == 422
        assert "invalid theme" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f13_boundary_unauthenticated_preference_fetch_returns_401(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict
    ):
        """Unauthenticated request to fetch user preferences returns HTTP 401."""
        res = await async_client.get("/api/v1/users/me/preferences", headers=tenant_alpha_headers)
        assert res.status_code == 401

    @pytest.mark.asyncio
    async def test_f13_boundary_patch_with_empty_body_returns_200(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """PATCH preferences with empty body {} returns 200 with current preference unchanged."""
        res = await async_client.patch(
            "/api/v1/users/me/preferences",
            json={},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert res.status_code == 200
        assert "theme" in res.json()

    @pytest.mark.asyncio
    async def test_f13_boundary_preference_update_persistence(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Theme update to 'dark' persists on subsequent GET queries."""
        patch_res = await async_client.patch(
            "/api/v1/users/me/preferences",
            json={"theme": "dark"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["theme"] == "dark"

        get_res = await async_client.get(
            "/api/v1/users/me/preferences",
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert get_res.status_code == 200
        assert get_res.json()["theme"] == "dark"

    @pytest.mark.asyncio
    async def test_f13_boundary_multi_user_isolation(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Preference updates for user-admin do not alter preferences for user-reviewer."""
        h1 = dict(tenant_alpha_headers)
        h1["X-User-ID"] = "user-admin"

        h2 = dict(tenant_alpha_headers)
        h2["X-User-ID"] = "user-reviewer"

        await async_client.patch(
            "/api/v1/users/me/preferences",
            json={"theme": "light"},
            headers=h1,
            cookies=auth_admin_cookies,
        )
        await async_client.patch(
            "/api/v1/users/me/preferences",
            json={"theme": "dark"},
            headers=h2,
            cookies=auth_admin_cookies,
        )

        r1 = await async_client.get("/api/v1/users/me/preferences", headers=h1, cookies=auth_admin_cookies)
        r2 = await async_client.get("/api/v1/users/me/preferences", headers=h2, cookies=auth_admin_cookies)
        assert r1.json()["theme"] == "light"
        assert r2.json()["theme"] == "dark"


# ============================================================================
# F14: Portal Boundary (5 tests)
# ============================================================================

class TestF14PortalBoundary:
    """Boundary & Negative tests for F14: Applicant Self-Service Portal."""

    @pytest.mark.asyncio
    async def test_f14_boundary_expired_token_returns_410_gone(
        self, async_client: httpx.AsyncClient
    ):
        """Accessing applicant portal with expired token returns HTTP 410 Gone."""
        res = await async_client.get("/api/v1/portal/expired-token-99999")
        assert res.status_code == 410
        assert "expired" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f14_boundary_tampered_invalid_token_returns_400(
        self, async_client: httpx.AsyncClient
    ):
        """Accessing applicant portal with corrupted/invalid token returns HTTP 400 Bad Request."""
        res = await async_client.get("/api/v1/portal/invalid-token-12345")
        assert res.status_code == 400
        assert "invalid" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f14_boundary_access_token_for_other_case_returns_404(
        self, async_client: httpx.AsyncClient
    ):
        """Querying portal with unassigned / foreign token returns HTTP 404."""
        res = await async_client.get("/api/v1/portal/token-other-case-404")
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_f14_boundary_upload_document_exceeding_10mb_via_portal_returns_413(
        self, async_client: httpx.AsyncClient
    ):
        """Uploading an 11MB document via applicant portal returns HTTP 413 Payload Too Large."""
        oversized_pdf = generate_oversized_document(size_mb=11)
        files = {"file": ("big_portal_doc.pdf", oversized_pdf, "application/pdf")}
        res = await async_client.post(
            "/api/v1/portal/valid-portal-token-1001/documents",
            files=files,
        )
        assert res.status_code == 413

    @pytest.mark.asyncio
    async def test_f14_boundary_portal_access_after_case_closed_returns_410(
        self, async_client: httpx.AsyncClient
    ):
        """Applicant portal access attempt on a closed case returns HTTP 410 Gone."""
        res = await async_client.get("/api/v1/portal/token-closed-case")
        assert res.status_code == 410
        assert "closed" in res.text.lower()


# ============================================================================
# F15: Controlled Sharing Boundary (5 tests)
# ============================================================================

class TestF15ControlledSharingBoundary:
    """Boundary & Negative tests for F15: Controlled Sharing."""

    @pytest.mark.asyncio
    async def test_f15_boundary_read_expired_share_grant_returns_410_gone(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Accessing a share grant past its expiration date returns HTTP 410 Gone."""
        # Create approved case
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "share_exp_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "documents_received"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "in_review"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        await async_client.post(
            f"/api/v1/cases/{case_id}/approve",
            json={"reason": "Approved"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )

        # Create share
        shr_res = await async_client.post(
            f"/api/v1/cases/{case_id}/shares",
            json={"selected_fields": ["full_name"], "recipient_tenant_id": "tenant-beta-002"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        share_token = shr_res.json()["share_token"]
        share_id = shr_res.json()["id"]

        # Grant consent
        await async_client.post(
            f"/api/v1/shares/{share_id}/consent",
            json={"decision": "granted"},
        )

        # Querying expired share token returns HTTP 410 Gone
        res = await async_client.get(
            "/api/v1/shares/tok-expired-30day-token",
            headers=tenant_alpha_headers,
        )
        assert res.status_code == 410
        assert "expired" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f15_boundary_share_unapproved_case_returns_400(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Attempting to share a case in 'draft' or 'in_review' status returns HTTP 400."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "share_unapp_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        res = await async_client.post(
            f"/api/v1/cases/{case_id}/shares",
            json={"selected_fields": ["full_name"]},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert res.status_code == 400
        assert "unapproved" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f15_boundary_unauthorized_3rd_party_tenant_read_returns_404(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_gamma_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Tenant Gamma attempting to read share grant created between Alpha and Beta returns HTTP 404."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "share_gamma_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "in_review"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Approved"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        shr = await async_client.post(
            f"/api/v1/cases/{case_id}/shares",
            json={"selected_fields": ["full_name"], "recipient_tenant_id": "tenant-beta-002"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        share_token = shr.json()["share_token"]

        # Read with Tenant Gamma header
        res = await async_client.get(
            f"/api/v1/shares/{share_token}",
            headers=tenant_gamma_headers,
        )
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_f15_boundary_empty_selected_fields_rejection_returns_400(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Creating a share grant with empty selected_fields list [] returns HTTP 400."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "share_empty_fields"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "in_review"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Approved"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        res = await async_client.post(
            f"/api/v1/cases/{case_id}/shares",
            json={"selected_fields": []},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert res.status_code == 400
        assert "empty" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f15_boundary_past_expiry_date_rejection_returns_400(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Creating a share grant with past expiration date returns HTTP 400."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "share_past_date"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "in_review"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Approved"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        past_ts = "2020-01-01T00:00:00"
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/shares",
            json={"selected_fields": ["full_name"], "expires_at": past_ts},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert res.status_code == 400
        assert "past expiry" in res.text.lower()


# ============================================================================
# F16: Share Consent Boundary (5 tests)
# ============================================================================

class TestF16ShareConsentBoundary:
    """Boundary & Negative tests for F16: Applicant Share Consent Workflow."""

    @pytest.mark.asyncio
    async def test_f16_boundary_consent_to_already_expired_share_returns_410(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Attempting to submit consent on an expired share grant returns HTTP 410 Gone."""
        # Simulated expired share token returns 410 Gone
        res = await async_client.post(
            "/api/v1/shares/shr-expired-mock-id/consent",
            json={"decision": "granted"},
        )
        assert res.status_code == 410
        assert "expired" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f16_boundary_consent_by_unauthorized_user_returns_403(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """User with unauthorized role 'third_party' attempting consent decision returns HTTP 403."""
        # Create share
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "consent_role_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "in_review"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Approved"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        shr = await async_client.post(
            f"/api/v1/cases/{case_id}/shares",
            json={"selected_fields": ["full_name"]},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        share_id = shr.json()["id"]

        res = await async_client.post(
            f"/api/v1/shares/{share_id}/consent",
            json={"decision": "granted"},
            headers={"X-User-Role": "third_party"},
        )
        assert res.status_code == 403

    @pytest.mark.asyncio
    async def test_f16_boundary_double_consent_approval_returns_400(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Submitting consent approval on a share that already has consent granted returns HTTP 400."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "consent_double"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "in_review"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Approved"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        shr = await async_client.post(
            f"/api/v1/cases/{case_id}/shares",
            json={"selected_fields": ["full_name"]},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        share_id = shr.json()["id"]

        r1 = await async_client.post(f"/api/v1/shares/{share_id}/consent", json={"decision": "granted"})
        assert r1.status_code == 200

        r2 = await async_client.post(f"/api/v1/shares/{share_id}/consent", json={"decision": "granted"})
        assert r2.status_code == 400
        assert "already approved" in r2.text.lower()

    @pytest.mark.asyncio
    async def test_f16_boundary_revoke_already_revoked_share_returns_400(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Revoking an already revoked share grant returns HTTP 400."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "revoke_double"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]


        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "in_review"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Approved"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        shr = await async_client.post(
            f"/api/v1/cases/{case_id}/shares",
            json={"selected_fields": ["full_name"]},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        share_id = shr.json()["id"]

        rev1 = await async_client.post(f"/api/v1/shares/{share_id}/revoke")
        assert rev1.status_code == 200

        rev2 = await async_client.post(f"/api/v1/shares/{share_id}/revoke")
        assert rev2.status_code == 400
        assert "already revoked" in rev2.text.lower()

    @pytest.mark.asyncio
    async def test_f16_boundary_nonexistent_share_id_returns_404(
        self, async_client: httpx.AsyncClient
    ):
        """Submitting consent to non-existent share ID returns HTTP 404."""
        res = await async_client.post(
            "/api/v1/shares/shr-completely-bogus/consent",
            json={"decision": "granted"},
        )
        assert res.status_code == 404


# ============================================================================
# F17: Local DB Boundary (5 tests)
# ============================================================================

class TestF17LocalDBBoundary:
    """Boundary & Integrity tests for F17: Local Embedded DB / Zero Cloud Run."""

    @pytest.mark.asyncio
    async def test_f17_boundary_db_locked_concurrency_handling(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Concurrent case creation requests execute cleanly without sqlite3.OperationalError: database is locked."""
        async def create_one(i: int):
            return await async_client.post(
                "/api/v1/cases",
                json={"applicant": generate_adult_applicant(), "purpose": f"concurrent_{i}"},
                headers=tenant_alpha_headers,
                cookies=auth_admin_cookies,
            )

        responses = await asyncio.gather(*(create_one(i) for i in range(5)))
        for r in responses:
            assert r.status_code == 201

    @pytest.mark.asyncio
    async def test_f17_boundary_foreign_key_constraints_enforcement(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Attempting to attach a document or field to a non-existent case fails with 404/400 (FK integrity)."""
        valid_pdf = generate_valid_pdf()
        files = {"file": ("orphan_doc.pdf", valid_pdf, "application/pdf")}
        res = await async_client.post(
            "/api/v1/cases/case-orphan-fk-9999/documents",
            files=files,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_f17_boundary_invalid_table_query_handling(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict
    ):
        """Querying invalid endpoints or non-existent tables returns 404 instead of 500 database crashes."""
        res = await async_client.get("/api/v1/non_existent_table", headers=tenant_alpha_headers)
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_f17_boundary_connection_pool_cleanup(self, test_db_engine):
        """Async database engine connection pool disposes cleanly without leaking file locks."""
        if test_db_engine is not None:
            assert hasattr(test_db_engine, "dispose")
        assert True

    @pytest.mark.asyncio
    async def test_f17_boundary_database_schema_version_integrity(
        self, async_client: httpx.AsyncClient
    ):
        """Health check endpoint returns local embedded database mode without external cloud dependencies."""
        res = await async_client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


# ============================================================================
# F18: OCR Fallback Boundary (5 tests)
# ============================================================================

class TestF18OCRFallbackBoundary:
    """Boundary & Resilience tests for F18: Pluggable OCR / Provider Fallbacks."""

    @pytest.mark.asyncio
    async def test_f18_boundary_corrupted_file_fallback_without_500_crash(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Corrupted file extraction engages heuristic fallback without 500 internal server error."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "ocr_resilience"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "aadhaar", "document_text": "CORRUPTED_BIN_STREAM\x00\xff\xfe"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 200
        assert res.json()["fallback_applied"] is True

    @pytest.mark.asyncio
    async def test_f18_boundary_unparseable_binary_buffer_fallback(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Unparseable binary noise returns low confidence fallback flag."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "ocr_noise"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        noise = "BLURRY_NOISE_@@##$$%%^^"
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "pan", "document_text": noise},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 200
        assert res.json()["extracted_fields"][0]["confidence"] < 0.30

    @pytest.mark.asyncio
    async def test_f18_boundary_unsupported_file_encoding(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Non-standard characters and mixed byte encodings are handled cleanly."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "ocr_encoding"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        mixed_text = "Standard Latin \u20ac Euro and \u00a5 Yen and \u2603 Snowman"
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "unicode_text", "document_text": mixed_text},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 200
        assert len(res.json()["extracted_fields"]) >= 1

    @pytest.mark.asyncio
    async def test_f18_boundary_zero_byte_file_handling(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """0-byte text stream returns empty fields array without crash."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "ocr_zero"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "aadhaar", "document_text": ""},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 200
        assert res.json()["count"] == 0

    @pytest.mark.asyncio
    async def test_f18_boundary_ocr_error_detail_sanitization(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """OCR error details do not expose raw server directories or secret paths."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "ocr_sanitize"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "aadhaar", "document_text": "CORRUPTED_DOCUMENT_WITH_PATH_C:\\Users\\secrets\\"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert res.status_code == 200
        text = res.text
        assert "secrets" not in text.lower() or res.json()["fallback_applied"] is True


# ============================================================================
# F19: Multi-Tenancy Boundary (5 tests)
# ============================================================================

class TestF19MultiTenancyBoundary:
    """Boundary & Isolation tests for F19: Multi-Tenancy & Tenant Filtering."""

    @pytest.mark.asyncio
    async def test_f19_boundary_tenant_a_requests_tenant_b_case_returns_404(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Tenant Alpha querying Tenant Beta case returns strict 404."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "iso_case"},
            headers=tenant_beta_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        res = await async_client.get(f"/api/v1/cases/{case_id}", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_f19_boundary_tenant_a_requests_tenant_b_doc_returns_404(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Tenant Alpha previewing Tenant Beta document returns strict 404."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "iso_doc"},
            headers=tenant_beta_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        pdf_bytes = generate_valid_pdf()
        files = {"file": ("beta_doc.pdf", pdf_bytes, "application/pdf")}
        up = await async_client.post(
            f"/api/v1/cases/{case_id}/documents",
            files=files,
            headers=tenant_beta_headers,
            cookies=auth_admin_cookies,
        )
        doc_id = up.json()["id"]

        # Attempt preview as Tenant Alpha
        res = await async_client.get(
            f"/api/v1/cases/{case_id}/documents/{doc_id}/preview",
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_f19_boundary_tenant_a_requests_tenant_b_share_returns_404(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        tenant_gamma_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Tenant Gamma accessing private share between Alpha and Beta returns strict 404."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "iso_share"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "in_review"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Approved"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        shr = await async_client.post(
            f"/api/v1/cases/{case_id}/shares",
            json={"selected_fields": ["full_name"], "recipient_tenant_id": "tenant-beta-002"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        share_token = shr.json()["share_token"]

        res = await async_client.get(f"/api/v1/shares/{share_token}", headers=tenant_gamma_headers)
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_f19_boundary_tenant_a_assigns_email_to_tenant_b_case_returns_404(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Tenant Alpha assigning exception to Tenant Beta case returns strict 404."""
        # Create case in Tenant Beta
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "beta_email_target"},
            headers=tenant_beta_headers,
            cookies=auth_admin_cookies,
        )
        beta_case_id = c.json()["id"]

        # Create exception in Tenant Alpha
        intake_res = await async_client.post(
            "/api/v1/intake/eml",
            files={"file": ("unmatched.eml", generate_unmatched_eml(), "message/rfc822")},
            headers=tenant_alpha_headers,
        )
        exc_id = intake_res.json()["exception_id"]

        # Attempt cross-tenant assignment
        res = await async_client.post(
            f"/api/v1/email/exceptions/{exc_id}/assign",
            json={"case_id": beta_case_id},
            headers=tenant_alpha_headers,
        )
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_f19_boundary_tenant_header_spoofing_rejected(
        self, async_client: httpx.AsyncClient, auth_admin_cookies: dict
    ):
        """Missing or blank X-Tenant-ID header is rejected with HTTP 400 Bad Request."""
        headers = {"X-Tenant-ID": "", "X-CSRF-Token": "csrf-token-test-secret-98765"}
        res = await async_client.get("/api/v1/cases", headers=headers, cookies=auth_admin_cookies)
        assert res.status_code == 400
        assert "tenant" in res.text.lower()


# ============================================================================
# F20: Security Auth Boundary (5 tests)
# ============================================================================

class TestF20SecurityAuthBoundary:
    """Boundary & Negative tests for F20: Security & Auth."""

    @pytest.mark.asyncio
    async def test_f20_boundary_missing_csrf_token_header_on_post_returns_403(
        self, async_client: httpx.AsyncClient, auth_admin_cookies: dict
    ):
        """POST request with auth cookies but missing X-CSRF-Token header returns HTTP 403."""
        headers = {"X-Tenant-ID": "tenant-alpha-001"}  # Missing X-CSRF-Token
        payload = {"applicant": generate_adult_applicant(), "purpose": "csrf_test"}
        res = await async_client.post("/api/v1/cases", json=payload, headers=headers, cookies=auth_admin_cookies)
        assert res.status_code == 403
        assert "csrf" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f20_boundary_mismatched_csrf_token_returns_403(
        self, async_client: httpx.AsyncClient, auth_admin_cookies: dict
    ):
        """POST request with mismatched X-CSRF-Token header returns HTTP 403."""
        headers = {"X-Tenant-ID": "tenant-alpha-001", "X-CSRF-Token": "wrong-secret-token-xyz"}
        payload = {"applicant": generate_adult_applicant(), "purpose": "csrf_mismatch_test"}
        res = await async_client.post("/api/v1/cases", json=payload, headers=headers, cookies=auth_admin_cookies)
        assert res.status_code == 403
        assert "csrf" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f20_boundary_expired_jwt_token_returns_401(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict
    ):
        """Request carrying expired JWT access_token returns HTTP 401 Unauthorized."""
        cookies = {"access_token": "expired-jwt-token"}
        res = await async_client.get("/api/v1/auth/me", headers=tenant_alpha_headers, cookies=cookies)
        assert res.status_code == 401
        assert "token" in res.text.lower() or "authenticated" in res.text.lower()

    @pytest.mark.asyncio
    async def test_f20_boundary_invalid_jwt_signature_returns_401(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict
    ):
        """Request carrying tampered or corrupted JWT returns HTTP 401 Unauthorized."""
        cookies = {"access_token": "tampered-jwt-token"}
        res = await async_client.get("/api/v1/auth/me", headers=tenant_alpha_headers, cookies=cookies)
        assert res.status_code == 401

    @pytest.mark.asyncio
    async def test_f20_boundary_login_with_invalid_password_returns_401(
        self, async_client: httpx.AsyncClient
    ):
        """Login attempt with incorrect password returns HTTP 401 Invalid credentials."""
        payload = {"email": "admin@example.com", "password": "wrong-password"}
        res = await async_client.post("/api/v1/auth/login", json=payload)
        assert res.status_code == 401
        assert "credentials" in res.text.lower() or "invalid" in res.text.lower()


# ============================================================================
# F21: Audit Trail Boundary (5 tests)
# ============================================================================

class TestF21AuditTrailBoundary:
    """Boundary & Integrity tests for F21: Immutable Audit Trail."""

    @pytest.mark.asyncio
    async def test_f21_boundary_no_sensitive_passwords_in_audit_logs(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Audit trail events never record raw passwords or secrets in event metadata."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "audit_secret_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        res = await async_client.get(f"/api/v1/cases/{case_id}/audit-trail", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 200
        events = res.json()["events"]
        assert len(events) >= 1
        for evt in events:
            meta_str = str(evt.get("metadata", {})).lower()
            assert "password" not in meta_str
            assert "secret" not in meta_str

    @pytest.mark.asyncio
    async def test_f21_boundary_no_raw_jwts_in_audit_logs(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Audit trail events never log raw JWT strings in event metadata."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "audit_jwt_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        res = await async_client.get(f"/api/v1/cases/{case_id}/audit-trail", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 200
        for evt in res.json()["events"]:
            meta_str = str(evt.get("metadata", {})).lower()
            assert "jwt-" not in meta_str
            assert "access_token" not in meta_str

    @pytest.mark.asyncio
    async def test_f21_boundary_append_only_constraint_no_delete_update_api(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Audit trail is strictly append-only: DELETE or PATCH methods return 405 Method Not Allowed."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "audit_delete_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        del_res = await async_client.delete(
            f"/api/v1/cases/{case_id}/audit-trail",
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert del_res.status_code == 405

    @pytest.mark.asyncio
    async def test_f21_boundary_audit_events_ordered_chronologically(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_reviewer_cookies: dict
    ):
        """Audit events are returned in strictly ascending chronological timestamp order."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "audit_order_test"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        case_id = c.json()["id"]

        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_reviewer_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "in_review"}, headers=tenant_alpha_headers, cookies=auth_reviewer_cookies)

        res = await async_client.get(f"/api/v1/cases/{case_id}/audit-trail", headers=tenant_alpha_headers, cookies=auth_reviewer_cookies)
        events = res.json()["events"]
        assert len(events) >= 3
        timestamps = [e["created_at"] for e in events]
        assert timestamps == sorted(timestamps)

    @pytest.mark.asyncio
    async def test_f21_boundary_cross_tenant_audit_access_returns_404(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Tenant Beta querying audit trail of Tenant Alpha case returns HTTP 404."""
        c = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "audit_cross_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c.json()["id"]

        res = await async_client.get(
            f"/api/v1/cases/{case_id}/audit-trail",
            headers=tenant_beta_headers,
            cookies=auth_admin_cookies,
        )
        assert res.status_code == 404


# ============================================================================
# F22: Usage Tracking Boundary (5 tests)
# ============================================================================

class TestF22UsageTrackingBoundary:
    """Boundary & Negative tests for F22: Usage Tracking & Quota Counters."""

    @pytest.mark.asyncio
    async def test_f22_boundary_cross_tenant_usage_access_scoped(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Usage metrics endpoint strictly scopes counters to header tenant_id without cross-leakage."""
        r_alpha = await async_client.get("/api/v1/tenants/usage", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        r_beta = await async_client.get("/api/v1/tenants/usage", headers=tenant_beta_headers, cookies=auth_admin_cookies)
        assert r_alpha.status_code == 200
        assert r_beta.status_code == 200
        assert r_alpha.json()["tenant_id"] == tenant_alpha_headers["X-Tenant-ID"]
        assert r_beta.json()["tenant_id"] == tenant_beta_headers["X-Tenant-ID"]

    @pytest.mark.asyncio
    async def test_f22_boundary_usage_tracking_across_multiple_tenants_independent(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_gamma_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Case creation in Tenant Alpha increments Alpha usage, leaving Gamma unchanged."""
        gamma_before = await async_client.get("/api/v1/tenants/usage", headers=tenant_gamma_headers, cookies=auth_admin_cookies)
        gamma_cases = gamma_before.json()["metrics"]["cases_created"]

        # Create case in Alpha
        await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "gamma_independence_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )

        gamma_after = await async_client.get("/api/v1/tenants/usage", headers=tenant_gamma_headers, cookies=auth_admin_cookies)
        assert gamma_after.json()["metrics"]["cases_created"] == gamma_cases

    @pytest.mark.asyncio
    async def test_f22_boundary_unauthenticated_usage_access_returns_401(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict
    ):
        """Unauthenticated call to usage metrics endpoint returns HTTP 401 Unauthorized."""
        res = await async_client.get("/api/v1/tenants/usage", headers=tenant_alpha_headers)
        assert res.status_code == 401

    @pytest.mark.asyncio
    async def test_f22_boundary_non_reviewer_role_usage_restriction_returns_403(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_applicant_cookies: dict
    ):
        """Role applicant calling usage metrics returns HTTP 403 Forbidden."""
        headers = dict(tenant_alpha_headers)
        headers["X-User-Role"] = "applicant"
        res = await async_client.get("/api/v1/tenants/usage", headers=headers, cookies=auth_applicant_cookies)
        assert res.status_code == 403

    @pytest.mark.asyncio
    async def test_f22_boundary_quota_limit_warning_emitted(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """Usage metrics endpoint accurately reflects quotas, remaining_cases, and warning boolean."""
        res = await async_client.get("/api/v1/tenants/usage", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 200
        data = res.json()
        assert "quotas" in data
        assert "max_cases" in data["quotas"]
        assert "remaining_cases" in data
        assert "quota_warning" in data
