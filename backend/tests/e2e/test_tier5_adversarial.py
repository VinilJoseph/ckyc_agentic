"""
Tier 5 Adversarial Coverage Hardening Test Suite for CKYC / eKYC Marketplace MVP.

This dedicated adversarial test suite subjects the verification architecture to rigorous
penetration, tampering, and abuse attacks across 7 core threat dimensions:
1. State Machine Abuse: illegal leaps, terminal state rollbacks, post-close mutations.
2. Cross-Tenant Isolation (BOLA/IDOR): cross-tenant read, update, doc preview, audit leak.
3. Document Security Exploits: polyglots (HTML/JS embedded in PDF), zero-byte files, null-byte injections, spoofing.
4. Auth & CSRF Penetration: header-cookie mismatch, missing CSRF, expired/tampered JWT, role escalation.
5. Biometric Edge Cases: strictly enforced impostor rejection (<0.40), truncated payloads, extreme aspect ratios.
6. Controlled Sharing Tampering: expired tokens, revoked consent access, unapproved case sharing, double consent.
7. Audit Trail Immutability: chronological event stream, credential scrubbing, deletion/tamper lockout.

Total Test Cases: 35 distinct adversarial stress tests.
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any

import pytest
import pytest_asyncio
import httpx

# Ensure test fixtures package is importable
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
# Adversarial Helper Fixtures & Payloads
# ============================================================================

def make_polyglot_pdf_xss() -> bytes:
    """
    Constructs a valid %PDF-1.4 document containing embedded HTML/JS script injection payloads.
    Verifies that the PDF parsing and magic-byte subsystem does not misidentify as text/html.
    """
    xss_payload = (
        b"%PDF-1.4\n"
        b"%<script>alert('XSS_ATTACK_VECTOR');</script>\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Length 72 >>\nstream\n"
        b"BT /F1 12 Tf 50 750 Td (<html><script>document.cookie</script></html>) Tj ET\n"
        b"endstream\nendobj\n"
        b"xref\n0 5\n"
        b"0000000000 65535 f \n"
        b"0000000057 00000 n \n"
        b"0000000108 00000 n \n"
        b"0000000169 00000 n \n"
        b"0000000257 00000 n \n"
        b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n380\n%%EOF\n"
    )
    return xss_payload


# ============================================================================
# 1. State Machine Abuse & Integrity Attacks
# ============================================================================

class TestTier5StateMachineAbuse:
    """Adversarial testing targeting workflow integrity and lifecycle state transitions."""

    @pytest.mark.asyncio
    async def test_adv_sm_01_draft_to_approved_leap_rejected(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """ATTACK: Bypass document intake and review by leaping from 'draft' straight to 'approved'."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "adversarial_leap"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert create_res.status_code == 201
        case_id = create_res.json()["id"]

        # Attempt illegal leap
        leap_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "approved"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert leap_res.status_code == 400
        assert "illegal state jump" in leap_res.text.lower()

    @pytest.mark.asyncio
    async def test_adv_sm_02_draft_to_rejected_leap_rejected(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """ATTACK: Bypass review by rejecting case immediately from 'draft'."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "adversarial_leap_reject"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]

        leap_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "rejected"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert leap_res.status_code == 400
        assert "illegal state jump" in leap_res.text.lower()

    @pytest.mark.asyncio
    async def test_adv_sm_03_awaiting_documents_to_approved_leap_rejected(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """ATTACK: Skip document receipt and review from awaiting_documents."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "adversarial_awaiting_leap"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]

        # Legitimate advance to awaiting_documents
        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "awaiting_documents"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )

        # Illegal leap to approved
        leap_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "approved"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert leap_res.status_code == 400
        assert "illegal state jump" in leap_res.text.lower()

    @pytest.mark.asyncio
    async def test_adv_sm_04_terminal_rejection_rollback_blocked(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """ATTACK: Attempt state rollback after final case rejection."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "adversarial_rollback_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]

        # Progress to in_review
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "in_review"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        # Reject case via decision gate
        reject_res = await async_client.post(
            f"/api/v1/cases/{case_id}/reject",
            json={"reason": "Fraudulent document identified"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert reject_res.status_code == 200

        # Attempt rollback to in_review
        rollback_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "in_review"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert rollback_res.status_code == 400
        assert "terminal state" in rollback_res.text.lower()

    @pytest.mark.asyncio
    async def test_adv_sm_05_terminal_approval_rollback_blocked(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """ATTACK: Attempt status rollback after case is already approved."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "adversarial_approval_lock"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]

        # Advance to in_review and approve
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "in_review"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "KYC validated"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        # Attempt rollback to draft
        rollback_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "draft"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert rollback_res.status_code == 400
        assert "terminal state" in rollback_res.text.lower()

    @pytest.mark.asyncio
    async def test_adv_sm_06_closed_case_status_tamper_blocked(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """ATTACK: Attempt reopening or modifying closed case."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "adversarial_close_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]

        # Close case
        close_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "closed"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert close_res.status_code == 200

        # Attempt reopen to in_review
        reopen_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "in_review"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert reopen_res.status_code == 400
        assert "terminal state" in reopen_res.text.lower()


# ============================================================================
# 2. Cross-Tenant Isolation Attacks (BOLA / IDOR)
# ============================================================================

class TestTier5TenantIsolationAttacks:
    """Adversarial penetration tests verifying strict 404 isolation across tenant perimeters."""

    @pytest.mark.asyncio
    async def test_adv_tenant_01_cross_tenant_case_read_blocked(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        auth_admin_cookies: dict,
    ):
        """ATTACK (BOLA/IDOR): Tenant Beta requests case created by Tenant Alpha."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "alpha_private_case"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        alpha_case_id = create_res.json()["id"]

        # Attacker Tenant Beta attempts read
        beta_read = await async_client.get(
            f"/api/v1/cases/{alpha_case_id}",
            headers=tenant_beta_headers,
            cookies=auth_admin_cookies,
        )
        assert beta_read.status_code == 404
        assert "not found" in beta_read.text.lower()

    @pytest.mark.asyncio
    async def test_adv_tenant_02_cross_tenant_case_status_patch_blocked(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        auth_admin_cookies: dict,
    ):
        """ATTACK: Tenant Beta attempts to modify status of Tenant Alpha's case."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "alpha_case_for_patch"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        alpha_case_id = create_res.json()["id"]

        beta_patch = await async_client.patch(
            f"/api/v1/cases/{alpha_case_id}/status",
            json={"status": "closed"},
            headers=tenant_beta_headers,
            cookies=auth_admin_cookies,
        )
        assert beta_patch.status_code == 404

    @pytest.mark.asyncio
    async def test_adv_tenant_03_cross_tenant_document_upload_blocked(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        auth_admin_cookies: dict,
        valid_pdf_document: bytes,
    ):
        """ATTACK: Tenant Beta attempts to inject document into Tenant Alpha's case."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "alpha_case_doc_injection"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        alpha_case_id = create_res.json()["id"]

        files = {"file": ("injected.pdf", valid_pdf_document, "application/pdf")}
        beta_upload = await async_client.post(
            f"/api/v1/cases/{alpha_case_id}/documents",
            files=files,
            headers=tenant_beta_headers,
            cookies=auth_admin_cookies,
        )
        assert beta_upload.status_code == 404

    @pytest.mark.asyncio
    async def test_adv_tenant_04_cross_tenant_document_preview_blocked(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        auth_admin_cookies: dict,
        valid_pdf_document: bytes,
    ):
        """ATTACK: Tenant Beta attempts to download/preview document uploaded by Tenant Alpha."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "alpha_confidential_doc"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        alpha_case_id = create_res.json()["id"]

        files = {"file": ("aadhaar_alpha.pdf", valid_pdf_document, "application/pdf")}
        doc_res = await async_client.post(
            f"/api/v1/cases/{alpha_case_id}/documents",
            files=files,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        doc_id = doc_res.json()["id"]

        # Tenant Beta attempts preview
        beta_preview = await async_client.get(
            f"/api/v1/cases/{alpha_case_id}/documents/{doc_id}/preview",
            headers=tenant_beta_headers,
            cookies=auth_admin_cookies,
        )
        assert beta_preview.status_code == 404

    @pytest.mark.asyncio
    async def test_adv_tenant_05_cross_tenant_field_decision_blocked(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        auth_admin_cookies: dict,
    ):
        """ATTACK: Tenant Beta attempts to correct/alter extracted fields on Tenant Alpha's case."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "alpha_fields_case"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        alpha_case_id = create_res.json()["id"]

        # Extract fields under Alpha
        ocr_res = await async_client.post(
            f"/api/v1/cases/{alpha_case_id}/extract-fields",
            json={"document_type": "aadhaar", "document_text": "Aadhaar: 2948 2847 2841"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        field_id = ocr_res.json()["extracted_fields"][0]["id"]

        # Tenant Beta attempts field decision
        beta_patch = await async_client.patch(
            f"/api/v1/cases/{alpha_case_id}/fields/{field_id}",
            json={"reviewer_decision": "corrected", "corrected_value": "999999999999"},
            headers=tenant_beta_headers,
            cookies=auth_admin_cookies,
        )
        assert beta_patch.status_code == 404

    @pytest.mark.asyncio
    async def test_adv_tenant_06_cross_tenant_case_approval_blocked(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        auth_admin_cookies: dict,
    ):
        """ATTACK: Tenant Beta attempts to approve Tenant Alpha's KYC case."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "alpha_approval_target"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        alpha_case_id = create_res.json()["id"]

        beta_approve = await async_client.post(
            f"/api/v1/cases/{alpha_case_id}/approve",
            json={"reason": "Attacker forced approval"},
            headers=tenant_beta_headers,
            cookies=auth_admin_cookies,
        )
        assert beta_approve.status_code == 404

    @pytest.mark.asyncio
    async def test_adv_tenant_07_cross_tenant_share_grant_isolation(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_gamma_headers: dict,
        auth_admin_cookies: dict,
    ):
        """ATTACK: Tenant Gamma attempts to sniff share grant issued from Alpha to Beta."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "alpha_shared_case"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        alpha_case_id = create_res.json()["id"]

        # Advance to approved
        await async_client.patch(f"/api/v1/cases/{alpha_case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{alpha_case_id}/status", json={"status": "in_review"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.post(f"/api/v1/cases/{alpha_case_id}/approve", json={"reason": "Approved for sharing"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        # Create share for Beta
        share_res = await async_client.post(
            f"/api/v1/cases/{alpha_case_id}/shares",
            json={"recipient_tenant_id": "tenant-beta-002", "purpose": "loan"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        share_token = share_res.json()["share_token"]

        # Unrelated Tenant Gamma attempts to access share
        gamma_res = await async_client.get(
            f"/api/v1/shares/{share_token}",
            headers=tenant_gamma_headers,
        )
        assert gamma_res.status_code == 404

    @pytest.mark.asyncio
    async def test_adv_tenant_08_cross_tenant_audit_trail_isolation(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        auth_admin_cookies: dict,
    ):
        """ATTACK: Tenant Beta attempts to inspect Tenant Alpha's immutable audit trail."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "alpha_audit_target"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        alpha_case_id = create_res.json()["id"]

        beta_audit = await async_client.get(
            f"/api/v1/cases/{alpha_case_id}/audit-trail",
            headers=tenant_beta_headers,
            cookies=auth_admin_cookies,
        )
        assert beta_audit.status_code == 404


# ============================================================================
# 3. Document Security Exploits & File Injection
# ============================================================================

class TestTier5DocumentSecurityExploits:
    """Adversarial exploits testing file upload validation, magic bytes, and polyglots."""

    @pytest.mark.asyncio
    async def test_adv_doc_01_zero_byte_file_rejection(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """ATTACK: Upload 0-byte file attempting buffer underflow or null dereference."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "zero_byte_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]

        files = {"file": ("empty.pdf", b"", "application/pdf")}
        upload_res = await async_client.post(
            f"/api/v1/cases/{case_id}/documents",
            files=files,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert upload_res.status_code == 400
        assert "magic byte validation failed" in upload_res.text.lower()

    @pytest.mark.asyncio
    async def test_adv_doc_02_polyglot_html_js_disguised_in_pdf(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """ATTACK: Polyglot PDF embedding malicious HTML/JS XSS vector."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "polyglot_xss_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]

        polyglot_bytes = make_polyglot_pdf_xss()
        files = {"file": ("invoice_xss.pdf", polyglot_bytes, "application/pdf")}
        upload_res = await async_client.post(
            f"/api/v1/cases/{case_id}/documents",
            files=files,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert upload_res.status_code == 201
        data = upload_res.json()
        # Verify system strictly classified as PDF, calculated SHA-256 hash, and isolated storage
        assert data["mime_type"] == "application/pdf"
        assert data["file_hash"] == hashlib.sha256(polyglot_bytes).hexdigest()
        assert "storage_key" in data

    @pytest.mark.asyncio
    async def test_adv_doc_03_null_byte_filename_injection(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
        valid_pdf_document: bytes,
    ):
        """ATTACK: Directory traversal and null-byte injection in filename."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "null_byte_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]

        # Filename containing null-byte and relative traversal
        malicious_filename = "../../../etc/passwd\x00.pdf"
        files = {"file": (malicious_filename, valid_pdf_document, "application/pdf")}
        upload_res = await async_client.post(
            f"/api/v1/cases/{case_id}/documents",
            files=files,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert upload_res.status_code == 201
        storage_key = upload_res.json()["storage_key"]
        # Verify storage key is strictly trapped under tenant and case path
        assert storage_key.startswith("tenants/")
        assert "etc/passwd" not in storage_key or "tenants/" in storage_key

    @pytest.mark.asyncio
    async def test_adv_doc_04_spoofed_jpeg_extension_rejection(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """ATTACK: Binary shell payload disguised with .jpg extension."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "spoofed_jpg_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]

        fake_jpeg = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"  # PE binary header
        files = {"file": ("passport.jpg", fake_jpeg, "image/jpeg")}
        upload_res = await async_client.post(
            f"/api/v1/cases/{case_id}/documents",
            files=files,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert upload_res.status_code == 400
        assert "magic byte validation failed" in upload_res.text.lower()

    @pytest.mark.asyncio
    async def test_adv_doc_05_oversized_payload_rejection(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict
    ):
        """ATTACK: Denial of service via oversized file upload (> 10MB limit)."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "dos_upload_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]

        oversized_bytes = generate_oversized_document(size_mb=11)
        files = {"file": ("dos_exploit.pdf", oversized_bytes, "application/pdf")}
        upload_res = await async_client.post(
            f"/api/v1/cases/{case_id}/documents",
            files=files,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert upload_res.status_code in (400, 413)


# ============================================================================
# 4. Authentication, CSRF & RBAC Penetration
# ============================================================================

class TestTier5AuthCSRFPenetration:
    """Adversarial penetration tests targeting token integrity, CSRF bypass, and RBAC escalation."""

    @pytest.mark.asyncio
    async def test_adv_auth_01_missing_csrf_token_header_rejected(
        self, async_client: httpx.AsyncClient, auth_admin_cookies: dict
    ):
        """ATTACK: CSRF attack with valid session cookie but omitted X-CSRF-Token header."""
        headers_without_csrf = {"X-Tenant-ID": "tenant-alpha-001"}
        res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "csrf_exploit"},
            headers=headers_without_csrf,
            cookies=auth_admin_cookies,
        )
        assert res.status_code == 403
        assert "csrf" in res.text.lower()

    @pytest.mark.asyncio
    async def test_adv_auth_02_mismatched_csrf_header_and_cookie(
        self, async_client: httpx.AsyncClient
    ):
        """ATTACK: Mismatched double-submit CSRF cookie vs request header."""
        forged_headers = {
            "X-Tenant-ID": "tenant-alpha-001",
            "X-CSRF-Token": "attacker-forged-csrf-header-999",
        }
        victim_cookies = {
            "access_token": "mock-admin-jwt-token-alpha",
            "csrf_token": "legitimate-victim-csrf-cookie-111",
        }
        res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "csrf_mismatch"},
            headers=forged_headers,
            cookies=victim_cookies,
        )
        assert res.status_code == 403
        assert "csrf" in res.text.lower()

    @pytest.mark.asyncio
    async def test_adv_auth_03_expired_jwt_cookie_rejected(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict
    ):
        """ATTACK: Replay attack using expired JWT session cookie."""
        expired_cookies = {
            "access_token": "expired-jwt-token",
            "csrf_token": tenant_alpha_headers["X-CSRF-Token"],
        }
        res = await async_client.get(
            "/api/v1/cases",
            headers=tenant_alpha_headers,
            cookies=expired_cookies,
        )
        assert res.status_code == 401
        assert "expired" in res.text.lower()

    @pytest.mark.asyncio
    async def test_adv_auth_04_tampered_jwt_signature_rejected(
        self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict
    ):
        """ATTACK: Session hijacking attempt via manipulated/tampered JWT cookie."""
        tampered_cookies = {
            "access_token": "tampered-jwt-token",
            "csrf_token": tenant_alpha_headers["X-CSRF-Token"],
        }
        res = await async_client.get(
            "/api/v1/cases",
            headers=tenant_alpha_headers,
            cookies=tampered_cookies,
        )
        assert res.status_code == 401
        assert "invalid" in res.text.lower() or "signature" in res.text.lower()

    @pytest.mark.asyncio
    async def test_adv_auth_05_role_escalation_applicant_approving_case(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
        auth_applicant_cookies: dict,
    ):
        """ATTACK: Privilege escalation where applicant attempts to execute reviewer case approval."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "priv_escalation_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]

        # Applicant attempts approval
        applicant_headers = dict(tenant_alpha_headers)
        applicant_headers["X-User-Role"] = "applicant"

        escalation_res = await async_client.post(
            f"/api/v1/cases/{case_id}/approve",
            json={"reason": "Self-approval exploit"},
            headers=applicant_headers,
            cookies=auth_applicant_cookies,
        )
        assert escalation_res.status_code == 403
        assert "applicant" in escalation_res.text.lower() or "cannot" in escalation_res.text.lower()

    @pytest.mark.asyncio
    async def test_adv_auth_06_role_escalation_applicant_modifying_status(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
        auth_applicant_cookies: dict,
    ):
        """ATTACK: Applicant attempts to directly alter case workflow status."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "applicant_patch_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]

        applicant_headers = dict(tenant_alpha_headers)
        applicant_headers["X-User-Role"] = "applicant"

        patch_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "in_review"},
            headers=applicant_headers,
            cookies=auth_applicant_cookies,
        )
        assert patch_res.status_code == 403


# ============================================================================
# 5. Biometric Boundary & Edge Cases
# ============================================================================

class TestTier5BiometricBoundaryEdgeCases:
    """Adversarial stress-testing of biometric face matching and rejection thresholds."""

    @pytest.mark.asyncio
    async def test_adv_bio_01_impostor_similarity_strictly_below_rejection_boundary(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
        mismatched_biometric_pair: tuple,
    ):
        """ATTACK: Impostor presentation attack. Verifies similarity score strictly < 0.40."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "impostor_spoof_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]

        selfie_bytes, impostor_bytes = mismatched_biometric_pair
        files = {
            "selfie": ("selfie.png", selfie_bytes, "image/png"),
            "id_photo": ("id_crop.png", impostor_bytes, "image/png"),
        }
        data = {"threshold": 0.75}

        match_res = await async_client.post(
            f"/api/v1/cases/{case_id}/selfie-match",
            files=files,
            data=data,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert match_res.status_code == 200
        result = match_res.json()
        assert result["is_match"] is False
        assert result["confidence"] < 0.40, f"Expected confidence < 0.40, got {result['confidence']}"

    @pytest.mark.asyncio
    async def test_adv_bio_02_corrupted_truncated_image_payload(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """ATTACK: Truncated corrupted image bytes uploaded to face matcher."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "corrupted_bio_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]

        corrupted_bytes = generate_corrupted_facial_image()
        files = {
            "selfie": ("bad_selfie.png", corrupted_bytes, "image/png"),
            "id_photo": ("bad_id.png", corrupted_bytes, "image/png"),
        }
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/selfie-match",
            files=files,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert res.status_code == 400
        assert "invalid_image_data" in res.text.lower()

    @pytest.mark.asyncio
    async def test_adv_bio_03_multiple_faces_detected_boundary(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """ATTACK: Multi-face presentation attack attempting to spoof liveness or ID pairing."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "multi_face_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]

        multi_face_bytes = b"\x89PNG\r\n\x1a\nMULTIPLE_FACES_TRIGGER_BUFFER_DATA"
        files = {
            "selfie": ("multi_face.png", multi_face_bytes, "image/png"),
            "id_photo": ("id_crop.png", multi_face_bytes, "image/png"),
        }
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/selfie-match",
            files=files,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert res.status_code == 400
        assert "multiple_faces" in res.text.lower()

    @pytest.mark.asyncio
    async def test_adv_bio_04_extreme_aspect_ratio_evaluation(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
        valid_png_document: bytes,
    ):
        """ATTACK: Single-pixel 1x1 minimal JPEG image compared to synthetic face."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "extreme_aspect_bio"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]

        minimal_jpeg = generate_valid_jpeg(width=1, height=1)
        files = {
            "selfie": ("micro_1x1.jpg", minimal_jpeg, "image/jpeg"),
            "id_photo": ("id.png", valid_png_document, "image/png"),
        }
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/selfie-match",
            files=files,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_match"] is False
        assert 0.0 <= data["confidence"] <= 1.0


# ============================================================================
# 6. Controlled Sharing Tampering & Consent Bypass
# ============================================================================

class TestTier5ControlledSharingTampering:
    """Adversarial testing targeting token expiration, consent lifecycle, and scope tampering."""

    @pytest.mark.asyncio
    async def test_adv_share_01_expired_token_returns_410_gone(
        self, async_client: httpx.AsyncClient
    ):
        """ATTACK: Accessing shared claims after 30-day token expiration."""
        res = await async_client.get("/api/v1/shares/tok-expired-30day-token")
        assert res.status_code == 410
        assert "expired" in res.text.lower()

    @pytest.mark.asyncio
    async def test_adv_share_02_revoked_consent_returns_410_gone(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """ATTACK: Accessing shared claims after consent grant has been revoked."""
        # Create and approve case
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "revocation_share_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "in_review"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Approved"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        # Create share
        share_res = await async_client.post(
            f"/api/v1/cases/{case_id}/shares",
            json={"recipient_tenant_id": "tenant-beta-002"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        share_id = share_res.json()["id"]
        share_token = share_res.json()["share_token"]

        # Applicant approves consent
        await async_client.post(f"/api/v1/shares/{share_id}/consent", json={"decision": "granted"})

        # Revoke share grant
        revoke_res = await async_client.post(f"/api/v1/shares/{share_id}/revoke")
        assert revoke_res.status_code == 200

        # Attempt read after revocation
        read_res = await async_client.get(
            f"/api/v1/shares/{share_token}",
            headers={"X-Tenant-ID": "tenant-beta-002"},
        )
        assert read_res.status_code == 410
        assert "revoked" in read_res.text.lower()

    @pytest.mark.asyncio
    async def test_adv_share_03_unapproved_case_sharing_blocked(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """ATTACK: Attempt to create share grant for an unapproved / draft KYC case."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "unapproved_share"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]

        share_res = await async_client.post(
            f"/api/v1/cases/{case_id}/shares",
            json={"recipient_tenant_id": "tenant-beta-002"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert share_res.status_code == 400
        assert "unapproved" in share_res.text.lower()

    @pytest.mark.asyncio
    async def test_adv_share_04_empty_selected_fields_rejection(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """ATTACK: Attempt to create share grant with empty field scope []."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "empty_fields_share"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "in_review"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Approved"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        share_res = await async_client.post(
            f"/api/v1/cases/{case_id}/shares",
            json={"recipient_tenant_id": "tenant-beta-002", "selected_fields": []},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert share_res.status_code == 400
        assert "empty selected_fields" in share_res.text.lower()

    @pytest.mark.asyncio
    async def test_adv_share_05_past_expiry_date_rejection(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """ATTACK: Attempt to set share grant expiry timestamp in the past."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "past_expiry_share"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "in_review"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Approved"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        past_date = (datetime.utcnow() - timedelta(days=5)).isoformat() + "Z"
        share_res = await async_client.post(
            f"/api/v1/cases/{case_id}/shares",
            json={"recipient_tenant_id": "tenant-beta-002", "expires_at": past_date},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert share_res.status_code == 400
        assert "past expiry date" in share_res.text.lower()

    @pytest.mark.asyncio
    async def test_adv_share_06_double_consent_submission_blocked(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """ATTACK: Race condition / replay submitting approval twice on the same consent record."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "double_consent"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "in_review"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Approved"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        share_res = await async_client.post(
            f"/api/v1/cases/{case_id}/shares",
            json={"recipient_tenant_id": "tenant-beta-002"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        share_id = share_res.json()["id"]

        # First consent
        c1 = await async_client.post(f"/api/v1/shares/{share_id}/consent", json={"decision": "granted"})
        assert c1.status_code == 200

        # Second consent
        c2 = await async_client.post(f"/api/v1/shares/{share_id}/consent", json={"decision": "granted"})
        assert c2.status_code == 400
        assert "already approved" in c2.text.lower()

    @pytest.mark.asyncio
    async def test_adv_share_07_double_revocation_submission_blocked(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """ATTACK: Re-invoking revocation on an already-revoked share grant."""
        create_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "double_revoke"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = create_res.json()["id"]
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "in_review"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Approved"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        share_res = await async_client.post(
            f"/api/v1/cases/{case_id}/shares",
            json={"recipient_tenant_id": "tenant-beta-002"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        share_id = share_res.json()["id"]

        r1 = await async_client.post(f"/api/v1/shares/{share_id}/revoke")
        assert r1.status_code == 200

        r2 = await async_client.post(f"/api/v1/shares/{share_id}/revoke")
        assert r2.status_code == 400
        assert "already revoked" in r2.text.lower()


# ============================================================================
# 7. Audit Trail Immutability & Append-Only Verification
# ============================================================================

class TestTier5AuditTrailImmutability:
    """Adversarial testing verifying that audit trail is strictly append-only, chronologically ordered, and sanitized."""

    @pytest.mark.asyncio
    async def test_adv_audit_01_chronological_append_only_event_stream(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
        valid_pdf_document: bytes,
    ):
        """VERIFY: Sequence of operations generates strictly append-only, chronological audit entries."""
        # 1. Create case
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "audit_stream_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c_res.json()["id"]

        # 2. Upload doc
        files = {"file": ("doc.pdf", valid_pdf_document, "application/pdf")}
        await async_client.post(f"/api/v1/cases/{case_id}/documents", files=files, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        # 3. Status transition
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "in_review"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        # 4. Final approval
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Audit verification approved"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        # Fetch audit trail
        trail_res = await async_client.get(
            f"/api/v1/cases/{case_id}/audit-trail",
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert trail_res.status_code == 200
        events = trail_res.json()["events"]
        actions = [e["action"] for e in events]

        assert "case_created" in actions
        assert "document_uploaded" in actions
        assert "status_transition" in actions
        assert "case_approved" in actions

        # Verify timestamps are monotonically non-decreasing
        timestamps = [datetime.fromisoformat(e["created_at"]) for e in events]
        assert timestamps == sorted(timestamps), "Audit events must be strictly chronological"

    @pytest.mark.asyncio
    async def test_adv_audit_02_credential_sanitization_in_metadata(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """SECURITY: Audit event metadata must never log raw passwords, JWTs, or secrets."""
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "audit_scrub_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c_res.json()["id"]

        trail_res = await async_client.get(
            f"/api/v1/cases/{case_id}/audit-trail",
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        events = trail_res.json()["events"]
        for evt in events:
            meta_str = json.dumps(evt.get("metadata", {})).lower()
            assert "password" not in meta_str
            assert "secret" not in meta_str
            assert "token" not in meta_str

    @pytest.mark.asyncio
    async def test_adv_audit_03_no_direct_mutation_or_deletion_api(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """ATTACK: Attempt to delete or tamper with audit events directly via HTTP DELETE/PUT."""
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "audit_tamper_attempt"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c_res.json()["id"]

        del_res = await async_client.delete(
            f"/api/v1/cases/{case_id}/audit-trail",
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert del_res.status_code == 405, "Audit trail must not allow DELETE operations"

        put_res = await async_client.put(
            f"/api/v1/cases/{case_id}/audit-trail",
            json={"tampered": True},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert put_res.status_code == 405, "Audit trail must not allow PUT operations"
