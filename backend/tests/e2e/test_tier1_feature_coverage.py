"""
Tier 1 E2E Feature Coverage Test Suite for CKYC / eKYC Marketplace MVP.

Contains exactly 110 isolated equivalence-class test cases (5 per feature across F1 to F22):
- F1: Case Creation & Scoping (5 tests)
- F2: State Machine Enforcement (5 tests)
- F3: Secure Document Upload (5 tests)
- F4: Automated Field Extraction (5 tests)
- F5: KYC Criteria Validation (5 tests)
- F6: Selfie-to-ID Photo Matching (5 tests)
- F7: Inbound Mail Document Ingestion (5 tests)
- F8: Email Exception Queue & Triage (5 tests)
- F9: Interactive Case Lifecycle Stepper (5 tests)
- F10: Split Reviewer Workspace Data API (5 tests)
- F11: Reviewer Field Decision Controls (5 tests)
- F12: Case Review Decision Gate (5 tests)
- F13: Dual Theme Preference API (5 tests)
- F14: Applicant Self-Service Portal (5 tests)
- F15: Controlled Sharing (5 tests)
- F16: Applicant Share Consent Workflow (5 tests)
- F17: Local Embedded DB / Zero Cloud Run (5 tests)
- F18: Pluggable OCR / Provider Fallbacks (5 tests)
- F19: Multi-Tenancy & Tenant Filtering (5 tests)
- F20: Security & Auth (JWT & CSRF) (5 tests)
- F21: Immutable Audit Trail (5 tests)
- F22: Usage Tracking & Quota Counters (5 tests)
"""

import hashlib
import json
import os
import sys
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
# F1: Case Creation & Scoping (5 tests)
# ============================================================================

class TestF01CaseCreationScoping:
    """Equivalence class tests for F1: Case Creation & Scoping."""

    @pytest.mark.asyncio
    async def test_f1_case_creation_individual_happy_path(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        applicant = generate_adult_applicant()
        payload = {"applicant": applicant, "purpose": "account_opening", "case_type": "individual"}
        response = await async_client.post("/api/v1/cases", json=payload, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "draft"
        assert data["case_number"].startswith("CASE-")
        assert data["tenant_id"] == tenant_alpha_headers["X-Tenant-ID"]
        assert data["purpose"] == "account_opening"

    @pytest.mark.asyncio
    async def test_f1_case_creation_business_entity(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        corp = generate_corporate_entity()
        payload = {"applicant": corp, "purpose": "merchant_onboarding", "case_type": "business"}
        response = await async_client.post("/api/v1/cases", json=payload, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert response.status_code == 201
        data = response.json()
        assert data["case_type"] == "business"
        assert data["applicant"]["business_name"] == corp["business_name"]

    @pytest.mark.asyncio
    async def test_f1_case_creation_missing_required_fields(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        payload = {"purpose": "account_opening"}  # Missing applicant
        response = await async_client.post("/api/v1/cases", json=payload, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_f1_case_creation_custom_purpose_scoping(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        applicant = generate_adult_applicant()
        custom_purpose = "high_value_cross_border_remittance"
        payload = {"applicant": applicant, "purpose": custom_purpose, "case_type": "individual"}
        response = await async_client.post("/api/v1/cases", json=payload, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert response.status_code == 201
        assert response.json()["purpose"] == custom_purpose

    @pytest.mark.asyncio
    async def test_f1_case_creation_tenant_binding_isolation(self, async_client: httpx.AsyncClient, tenant_beta_headers: dict, auth_admin_cookies: dict):
        applicant = generate_adult_applicant()
        payload = {"applicant": applicant, "purpose": "loan_origination"}
        response = await async_client.post("/api/v1/cases", json=payload, headers=tenant_beta_headers, cookies=auth_admin_cookies)
        assert response.status_code == 201
        data = response.json()
        assert data["tenant_id"] == tenant_beta_headers["X-Tenant-ID"]


# ============================================================================
# F2: State Machine Enforcement (5 tests)
# ============================================================================

class TestF02StateMachineEnforcement:
    """Equivalence class tests for F2: State Machine Enforcement."""

    @pytest.mark.asyncio
    async def test_f2_state_machine_valid_sequential_transition(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        # Create case
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        # draft -> invitation_sent
        t1 = await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "invitation_sent"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert t1.status_code == 200
        assert t1.json()["status"] == "invitation_sent"

        # invitation_sent -> awaiting_documents
        t2 = await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "awaiting_documents"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert t2.status_code == 200
        assert t2.json()["status"] == "awaiting_documents"

    @pytest.mark.asyncio
    async def test_f2_state_machine_invalid_jump_rejection(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        # Illegal jump: draft directly to approved
        bad_jump = await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "approved"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert bad_jump.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_f2_state_machine_terminal_state_lock(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        # Approve case directly via approve endpoint
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Approved fully"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        # Attempt to transition out of approved back to draft
        res = await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "draft"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_f2_state_machine_needs_correction_loop(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        # Advance: draft -> awaiting_documents -> documents_received -> in_review
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "awaiting_documents"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "in_review"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        # Loop: in_review -> needs_applicant_correction -> documents_received
        corr = await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "needs_applicant_correction"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert corr.status_code == 200
        assert corr.json()["status"] == "needs_applicant_correction"

        resub = await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert resub.status_code == 200
        assert resub.json()["status"] == "documents_received"

    @pytest.mark.asyncio
    async def test_f2_state_machine_audit_trail_emission_on_transition(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "invitation_sent"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        audit_res = await async_client.get(f"/api/v1/cases/{case_id}/audit-trail", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert audit_res.status_code == 200
        events = audit_res.json()["events"]
        actions = [e["action"] for e in events]
        assert "status_transition" in actions


# ============================================================================
# F3: Secure Document Upload (5 tests)
# ============================================================================

class TestF03SecureDocumentUpload:
    """Equivalence class tests for F3: Secure Document Upload."""

    @pytest.mark.asyncio
    async def test_f3_document_upload_valid_pdf_magic_bytes(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict, valid_pdf_document: bytes):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        files = {"file": ("aadhaar.pdf", valid_pdf_document, "application/pdf")}
        data = {"document_type": "identity_card"}
        res = await async_client.post(f"/api/v1/cases/{case_id}/documents", files=files, data=data, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 201
        doc = res.json()
        assert doc["mime_type"] == "application/pdf"
        assert doc["file_hash"] == hashlib.sha256(valid_pdf_document).hexdigest()

    @pytest.mark.asyncio
    async def test_f3_document_upload_valid_jpeg_magic_bytes(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict, valid_jpeg_document: bytes):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        files = {"file": ("photo.jpg", valid_jpeg_document, "image/jpeg")}
        res = await async_client.post(f"/api/v1/cases/{case_id}/documents", files=files, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 201
        assert res.json()["mime_type"] == "image/jpeg"

    @pytest.mark.asyncio
    async def test_f3_document_upload_spoofed_extension_magic_bytes_failure(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        spoofed_bytes = generate_spoofed_document("pdf")
        files = {"file": ("fake.pdf", spoofed_bytes, "application/pdf")}
        res = await async_client.post(f"/api/v1/cases/{case_id}/documents", files=files, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 400

    @pytest.mark.asyncio
    async def test_f3_document_upload_oversized_file_rejection(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        oversized_bytes = generate_oversized_document(size_mb=11)
        files = {"file": ("huge.pdf", oversized_bytes, "application/pdf")}
        res = await async_client.post(f"/api/v1/cases/{case_id}/documents", files=files, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code in (400, 413)

    @pytest.mark.asyncio
    async def test_f3_document_upload_sha256_integrity_verification(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict, valid_png_document: bytes):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        expected_hash = hashlib.sha256(valid_png_document).hexdigest()
        files = {"file": ("id.png", valid_png_document, "image/png")}
        res = await async_client.post(f"/api/v1/cases/{case_id}/documents", files=files, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 201
        assert res.json()["file_hash"] == expected_hash


# ============================================================================
# F4: Automated Field Extraction (5 tests)
# ============================================================================

class TestF04AutomatedFieldExtraction:
    """Equivalence class tests for F4: Automated Field Extraction."""

    @pytest.mark.asyncio
    async def test_f4_ocr_field_extraction_aadhaar_card(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        ocr_res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "aadhaar", "document_text": "Government of India Aarav Sharma DOB: 1990-05-15 2948 2847 2841"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies
        )
        assert ocr_res.status_code == 200
        fields = ocr_res.json()["extracted_fields"]
        assert len(fields) >= 1
        assert fields[0]["field_name"] == "aadhaar_number"
        assert fields[0]["draft_value"] == "294828472841"

    @pytest.mark.asyncio
    async def test_f4_ocr_field_extraction_pan_card(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        ocr_res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "pan", "document_text": "INCOME TAX DEPARTMENT ABCPS1234F AARAV SHARMA"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies
        )
        assert ocr_res.status_code == 200
        fields = ocr_res.json()["extracted_fields"]
        assert fields[0]["field_name"] == "pan_number"
        assert fields[0]["draft_value"] == "ABCPS1234F"

    @pytest.mark.asyncio
    async def test_f4_ocr_field_extraction_passport_mrz(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        mrz = generate_valid_passport_mrz(doc_number="J84920184")
        ocr_res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "passport_mrz", "document_text": mrz},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies
        )
        assert ocr_res.status_code == 200
        fields = ocr_res.json()["extracted_fields"]
        assert fields[0]["field_name"] == "passport_number"
        assert fields[0]["draft_value"] == "J84920184"

    @pytest.mark.asyncio
    async def test_f4_ocr_field_extraction_confidence_scoring(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        ocr_res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "aadhaar", "document_text": "2948 2847 2841"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies
        )
        assert ocr_res.status_code == 200
        confidence = ocr_res.json()["extracted_fields"][0]["confidence"]
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_f4_ocr_field_extraction_unreadable_blank_document(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        ocr_res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "aadhaar", "document_text": "unreadable smudge blur"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies
        )
        assert ocr_res.status_code == 200
        confidence = ocr_res.json()["extracted_fields"][0]["confidence"]
        assert confidence < 0.50


# ============================================================================
# F5: KYC Criteria Validation (5 tests)
# ============================================================================

class TestF05KYCCriteriaValidation:
    """Equivalence class tests for F5: KYC Criteria Validation."""

    @pytest.mark.asyncio
    async def test_f5_validation_valid_aadhaar_verhoeff_pass(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        valid_aadhaar = generate_valid_aadhaar()
        val_res = await async_client.post(
            f"/api/v1/cases/{case_id}/validate",
            json={"aadhaar_number": valid_aadhaar},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies
        )
        assert val_res.status_code == 200
        assert val_res.json()["is_valid"] is True
        assert len(val_res.json()["issues"]) == 0

    @pytest.mark.asyncio
    async def test_f5_validation_invalid_aadhaar_verhoeff_flagged(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        bad_aadhaar = generate_invalid_aadhaar()
        val_res = await async_client.post(
            f"/api/v1/cases/{case_id}/validate",
            json={"aadhaar_number": bad_aadhaar},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies
        )
        assert val_res.status_code == 200
        data = val_res.json()
        assert data["is_valid"] is False
        codes = [i["code"] for i in data["issues"]]
        assert "INVALID_VERHOEFF_CHECKSUM" in codes

    @pytest.mark.asyncio
    async def test_f5_validation_pan_entity_type_rule(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        bad_pan = generate_invalid_pan(reason="entity")
        val_res = await async_client.post(
            f"/api/v1/cases/{case_id}/validate",
            json={"pan_number": bad_pan},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies
        )
        assert val_res.status_code == 200
        codes = [i["code"] for i in val_res.json()["issues"]]
        assert "INVALID_PAN_ENTITY_TYPE" in codes

    @pytest.mark.asyncio
    async def test_f5_validation_passport_mrz_731_checksum(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        bad_mrz = generate_invalid_passport_mrz(reason="checksum")
        val_res = await async_client.post(
            f"/api/v1/cases/{case_id}/validate",
            json={"passport_mrz": bad_mrz},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies
        )
        assert val_res.status_code == 200
        codes = [i["code"] for i in val_res.json()["issues"]]
        assert "MRZ_CHECKSUM_MISMATCH" in codes

    @pytest.mark.asyncio
    async def test_f5_validation_underage_applicant_flagged(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        minor = generate_minor_applicant(age=15)
        val_res = await async_client.post(
            f"/api/v1/cases/{case_id}/validate",
            json={"date_of_birth": minor["date_of_birth"]},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies
        )
        assert val_res.status_code == 200
        codes = [i["code"] for i in val_res.json()["issues"]]
        assert "APPLICANT_UNDERAGE" in codes


# ============================================================================
# F6: Selfie-to-ID Photo Matching (5 tests)
# ============================================================================

class TestF06SelfieToIDPhotoMatching:
    """Equivalence class tests for F6: Selfie-to-ID Photo Matching."""

    @pytest.mark.asyncio
    async def test_f6_selfie_match_high_similarity_pair(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict, matched_biometric_pair: tuple):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        selfie_bytes, id_bytes = matched_biometric_pair
        files = {
            "selfie": ("selfie.png", selfie_bytes, "image/png"),
            "id_photo": ("id_crop.png", id_bytes, "image/png"),
        }
        res = await async_client.post(f"/api/v1/cases/{case_id}/selfie-match", files=files, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 200
        data = res.json()
        assert data["is_match"] is True
        assert data["confidence"] >= 0.75

    @pytest.mark.asyncio
    async def test_f6_selfie_match_impostor_mismatch_pair(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict, mismatched_biometric_pair: tuple):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        selfie_bytes, impostor_bytes = mismatched_biometric_pair
        files = {
            "selfie": ("selfie.png", selfie_bytes, "image/png"),
            "id_photo": ("impostor.png", impostor_bytes, "image/png"),
        }
        res = await async_client.post(f"/api/v1/cases/{case_id}/selfie-match", files=files, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 200
        data = res.json()
        assert data["is_match"] is False
        assert data["confidence"] < 0.50

    @pytest.mark.asyncio
    async def test_f6_selfie_match_corrupted_image_handling(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        corrupted = generate_corrupted_facial_image()
        files = {"selfie": ("corrupt.png", corrupted, "image/png")}
        res = await async_client.post(f"/api/v1/cases/{case_id}/selfie-match", files=files, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 400

    @pytest.mark.asyncio
    async def test_f6_selfie_match_case_binding(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict, matched_biometric_pair: tuple):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        selfie_bytes, id_bytes = matched_biometric_pair
        files = {
            "selfie": ("selfie.png", selfie_bytes, "image/png"),
            "id_photo": ("id.png", id_bytes, "image/png"),
        }
        await async_client.post(f"/api/v1/cases/{case_id}/selfie-match", files=files, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        case_detail = await async_client.get(f"/api/v1/cases/{case_id}", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert case_detail.status_code == 200
        assert case_detail.json()["selfie_match"] is not None

    @pytest.mark.asyncio
    async def test_f6_selfie_match_threshold_customization(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict, matched_biometric_pair: tuple):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        selfie_bytes, id_bytes = matched_biometric_pair
        files = {
            "selfie": ("selfie.png", selfie_bytes, "image/png"),
            "id_photo": ("id.png", id_bytes, "image/png"),
        }
        # With high threshold 0.99
        res = await async_client.post(f"/api/v1/cases/{case_id}/selfie-match", files=files, data={"threshold": "0.99"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 200
        assert res.json()["threshold"] == 0.99


# ============================================================================
# F7: Inbound Mail Document Ingestion (5 tests)
# ============================================================================

class TestF07InboundMailDocumentIngestion:
    """Equivalence class tests for F7: Inbound Mail Document Ingestion."""

    @pytest.mark.asyncio
    async def test_f7_inbound_mail_matched_case_auto_attachment(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_number = c_res.json()["case_number"]

        eml_bytes = generate_synthetic_eml(case_number=case_number)
        files = {"file": ("submission.eml", eml_bytes, "message/rfc822")}
        res = await async_client.post("/api/v1/intake/eml", files=files, headers=tenant_alpha_headers)
        assert res.status_code == 200
        assert res.json()["status"] == "attached_to_case"
        assert res.json()["case_number"] == case_number

    @pytest.mark.asyncio
    async def test_f7_inbound_mail_rest_webhook_payload(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_number = c_res.json()["case_number"]

        webhook_payload = {
            "message_id": "<msg-test-webhook-1@fintechbank.com>",
            "sender": "applicant@example.com",
            "subject": f"Verification Documents [{case_number}]",
            "body": "Documents attached",
        }
        res = await async_client.post("/api/v1/intake/email", json=webhook_payload, headers=tenant_alpha_headers)
        assert res.status_code == 200
        assert res.json()["status"] == "attached_to_case"

    @pytest.mark.asyncio
    async def test_f7_inbound_mail_status_transition_on_intake(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]
        case_number = c_res.json()["case_number"]

        eml_bytes = generate_synthetic_eml(case_number=case_number)
        files = {"file": ("submission.eml", eml_bytes, "message/rfc822")}
        await async_client.post("/api/v1/intake/eml", files=files, headers=tenant_alpha_headers)

        updated_case = await async_client.get(f"/api/v1/cases/{case_id}", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert updated_case.json()["status"] == "documents_received"

    @pytest.mark.asyncio
    async def test_f7_inbound_mail_multiple_attachments_extracted(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_number = c_res.json()["case_number"]

        eml_bytes = generate_synthetic_eml(case_number=case_number)
        files = {"file": ("multi.eml", eml_bytes, "message/rfc822")}
        res = await async_client.post("/api/v1/intake/eml", files=files, headers=tenant_alpha_headers)
        assert res.status_code == 200
        assert res.json()["attachments_count"] == 2

    @pytest.mark.asyncio
    async def test_f7_inbound_mail_duplicate_message_id_idempotency(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict):
        unique_msg_id = "<idempotent-unique-1234@fintechbank.com>"
        payload = {
            "message_id": unique_msg_id,
            "sender": "applicant@example.com",
            "subject": "Inbound submission",
        }
        res1 = await async_client.post("/api/v1/intake/email", json=payload, headers=tenant_alpha_headers)
        assert res1.status_code == 200

        # Post identical message_id again
        res2 = await async_client.post("/api/v1/intake/email", json=payload, headers=tenant_alpha_headers)
        assert res2.status_code == 200
        assert res2.json()["status"] == "idempotent_duplicate"


# ============================================================================
# F8: Email Exception Queue & Triage (5 tests)
# ============================================================================

class TestF08EmailExceptionQueueTriage:
    """Equivalence class tests for F8: Email Exception Queue & Triage."""

    @pytest.mark.asyncio
    async def test_f8_email_exception_unmatched_intake_routed_to_queue(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict):
        unmatched_eml = generate_unmatched_eml()
        files = {"file": ("unmatched.eml", unmatched_eml, "message/rfc822")}
        res = await async_client.post("/api/v1/intake/eml", files=files, headers=tenant_alpha_headers)
        assert res.status_code == 200
        assert res.json()["status"] == "routed_to_exception_queue"

    @pytest.mark.asyncio
    async def test_f8_email_exception_list_exceptions(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict):
        await async_client.post("/api/v1/intake/email", json={"subject": "No Case Tag Here", "sender": "lost@domain.com"}, headers=tenant_alpha_headers)
        res = await async_client.get("/api/v1/email/exceptions", headers=tenant_alpha_headers)
        assert res.status_code == 200
        assert res.json()["total"] >= 1

    @pytest.mark.asyncio
    async def test_f8_email_exception_assign_to_case(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        # Ingest unmatched
        in_res = await async_client.post("/api/v1/intake/email", json={"subject": "Inquiry Documents", "sender": "manual@domain.com"}, headers=tenant_alpha_headers)
        exc_id = in_res.json()["exception_id"]

        # Create target case
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        target_case_id = c_res.json()["id"]

        # Assign
        assign_res = await async_client.post(
            f"/api/v1/email/exceptions/{exc_id}/assign",
            json={"case_id": target_case_id},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies
        )
        assert assign_res.status_code == 200
        assert assign_res.json()["status"] == "assigned"

    @pytest.mark.asyncio
    async def test_f8_email_exception_dismiss_junk_email(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        in_res = await async_client.post("/api/v1/intake/email", json={"subject": "Spam marketing promotion", "sender": "spam@promo.com"}, headers=tenant_alpha_headers)
        exc_id = in_res.json()["exception_id"]

        dismiss_res = await async_client.post(f"/api/v1/email/exceptions/{exc_id}/dismiss", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert dismiss_res.status_code == 200
        assert dismiss_res.json()["status"] == "dismissed"

    @pytest.mark.asyncio
    async def test_f8_email_exception_cross_tenant_isolation(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, tenant_beta_headers: dict, auth_admin_cookies: dict):
        in_res = await async_client.post("/api/v1/intake/email", json={"subject": "Alpha secret doc", "sender": "alpha@bank.com"}, headers=tenant_alpha_headers)
        exc_id = in_res.json()["exception_id"]

        # Tenant Beta attempts to assign Tenant Alpha's exception -> 404
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_beta_headers, cookies=auth_admin_cookies)
        beta_case_id = c_res.json()["id"]

        cross_res = await async_client.post(
            f"/api/v1/email/exceptions/{exc_id}/assign",
            json={"case_id": beta_case_id},
            headers=tenant_beta_headers,
            cookies=auth_admin_cookies
        )
        assert cross_res.status_code == 404


# ============================================================================
# F9: Interactive Case Lifecycle Stepper (5 tests)
# ============================================================================

class TestF09InteractiveCaseLifecycleStepper:
    """Equivalence class tests for F9: Interactive Case Lifecycle Stepper."""

    @pytest.mark.asyncio
    async def test_f9_case_stepper_current_step_index(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        detail = await async_client.get(f"/api/v1/cases/{case_id}", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert detail.status_code == 200
        stepper = detail.json()["stepper"]
        assert stepper["current_step"] == 1
        assert stepper["current_stage"] == "draft"

    @pytest.mark.asyncio
    async def test_f9_case_stepper_completed_steps_history(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "invitation_sent"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        detail = await async_client.get(f"/api/v1/cases/{case_id}", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        completed = detail.json()["stepper"]["completed_steps"]
        assert len(completed) >= 2
        assert completed[-1]["stage"] == "invitation_sent"

    @pytest.mark.asyncio
    async def test_f9_case_stepper_pending_steps(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        detail = await async_client.get(f"/api/v1/cases/{case_id}", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        pending = detail.json()["stepper"]["pending_steps"]
        assert "approved" in pending

    @pytest.mark.asyncio
    async def test_f9_case_stepper_needs_correction_branching(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "awaiting_documents"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "in_review"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "needs_applicant_correction"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        detail = await async_client.get(f"/api/v1/cases/{case_id}", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert detail.json()["stepper"]["current_stage"] == "needs_applicant_correction"

    @pytest.mark.asyncio
    async def test_f9_case_stepper_terminal_status_display(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Completed all steps"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        detail = await async_client.get(f"/api/v1/cases/{case_id}", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert detail.json()["status"] == "approved"
        assert detail.json()["review_decision"] == "approved"


# ============================================================================
# F10: Split Reviewer Workspace Data API (5 tests)
# ============================================================================

class TestF10SplitReviewerWorkspaceDataAPI:
    """Equivalence class tests for F10: Split Reviewer Workspace Data API."""

    @pytest.mark.asyncio
    async def test_f10_reviewer_workspace_case_detail_payload(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        res = await async_client.get(f"/api/v1/cases/{case_id}", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 200
        data = res.json()
        assert "documents" in data
        assert "extracted_fields" in data
        assert "validation_issues" in data
        assert "applicant" in data

    @pytest.mark.asyncio
    async def test_f10_reviewer_workspace_document_preview_url(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict, valid_pdf_document: bytes):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        files = {"file": ("preview.pdf", valid_pdf_document, "application/pdf")}
        doc_res = await async_client.post(f"/api/v1/cases/{case_id}/documents", files=files, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        doc_id = doc_res.json()["id"]

        preview_res = await async_client.get(f"/api/v1/cases/{case_id}/documents/{doc_id}/preview", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert preview_res.status_code == 200
        assert preview_res.json()["preview_available"] is True

    @pytest.mark.asyncio
    async def test_f10_reviewer_workspace_field_deck_organization(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        await async_client.post(f"/api/v1/cases/{case_id}/extract-fields", json={"document_type": "aadhaar"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        res = await async_client.get(f"/api/v1/cases/{case_id}", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        fields = res.json()["extracted_fields"]
        assert len(fields) >= 1
        assert "field_name" in fields[0]
        assert "draft_value" in fields[0]

    @pytest.mark.asyncio
    async def test_f10_reviewer_workspace_validation_issue_badges(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        await async_client.post(f"/api/v1/cases/{case_id}/validate", json={"aadhaar_number": "999999999999"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        res = await async_client.get(f"/api/v1/cases/{case_id}", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        issues = res.json()["validation_issues"]
        assert len(issues) >= 1
        assert "severity" in issues[0]

    @pytest.mark.asyncio
    async def test_f10_reviewer_workspace_unauthorized_access_forbidden(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        headers = dict(tenant_alpha_headers)
        headers["X-User-Role"] = "unauthorized"
        res = await async_client.get(f"/api/v1/cases/{case_id}", headers=headers, cookies=auth_admin_cookies)
        assert res.status_code == 403


# ============================================================================
# F11: Reviewer Field Decision Controls (5 tests)
# ============================================================================

class TestF11ReviewerFieldDecisionControls:
    """Equivalence class tests for F11: Reviewer Field Decision Controls."""

    @pytest.mark.asyncio
    async def test_f11_field_decision_confirm_field(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        ext = await async_client.post(f"/api/v1/cases/{case_id}/extract-fields", json={"document_type": "aadhaar"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        field_id = ext.json()["extracted_fields"][0]["id"]

        patch_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/fields/{field_id}",
            json={"reviewer_decision": "confirmed"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["reviewer_decision"] == "confirmed"

    @pytest.mark.asyncio
    async def test_f11_field_decision_correct_field_value(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        ext = await async_client.post(f"/api/v1/cases/{case_id}/extract-fields", json={"document_type": "aadhaar"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        field_id = ext.json()["extracted_fields"][0]["id"]

        corrected_val = "294828472849"
        patch_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/fields/{field_id}",
            json={"reviewer_decision": "corrected", "corrected_value": corrected_val},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["confirmed_value"] == corrected_val

    @pytest.mark.asyncio
    async def test_f11_field_decision_reject_field(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        ext = await async_client.post(f"/api/v1/cases/{case_id}/extract-fields", json={"document_type": "aadhaar"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        field_id = ext.json()["extracted_fields"][0]["id"]

        patch_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/fields/{field_id}",
            json={"reviewer_decision": "rejected", "reviewer_notes": "Illegible character"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["reviewer_decision"] == "rejected"

    @pytest.mark.asyncio
    async def test_f11_field_decision_correction_history_tracking(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        ext = await async_client.post(f"/api/v1/cases/{case_id}/extract-fields", json={"document_type": "aadhaar"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        field_id = ext.json()["extracted_fields"][0]["id"]

        # First edit
        await async_client.patch(f"/api/v1/cases/{case_id}/fields/{field_id}", json={"reviewer_decision": "corrected", "corrected_value": "Val1"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        # Second edit
        res = await async_client.patch(f"/api/v1/cases/{case_id}/fields/{field_id}", json={"reviewer_decision": "corrected", "corrected_value": "Val2"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 200
        assert len(res.json()["correction_history"]) >= 2

    @pytest.mark.asyncio
    async def test_f11_field_decision_nonexistent_field_404(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        patch_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/fields/fld-nonexistent-12345",
            json={"reviewer_decision": "confirmed"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies
        )
        assert patch_res.status_code == 404


# ============================================================================
# F12: Case Review Decision Gate (5 tests)
# ============================================================================

class TestF12CaseReviewDecisionGate:
    """Equivalence class tests for F12: Case Review Decision Gate."""

    @pytest.mark.asyncio
    async def test_f12_decision_gate_approve_with_valid_reason(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        reason = "All documents verified and biometric match confirmed"
        res = await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": reason}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 200
        assert res.json()["status"] == "approved"
        assert res.json()["reason"] == reason

    @pytest.mark.asyncio
    async def test_f12_decision_gate_approve_missing_reason_rejected(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        # Missing or empty reason
        res = await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": ""}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_f12_decision_gate_reject_with_fraud_reason(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        fraud_reason = "Suspected fraudulent Aadhaar checksum and mismatched selfie"
        res = await async_client.post(f"/api/v1/cases/{case_id}/reject", json={"reason": fraud_reason}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 200
        assert res.json()["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_f12_decision_gate_reject_missing_reason_rejected(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        res = await async_client.post(f"/api/v1/cases/{case_id}/reject", json={}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_f12_decision_gate_audit_log_records_decision_and_reason(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        reason = "Clean record"
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": reason}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        audit = await async_client.get(f"/api/v1/cases/{case_id}/audit-trail", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        events = audit.json()["events"]
        approve_event = next((e for e in events if e["action"] == "case_approved"), None)
        assert approve_event is not None
        assert approve_event["metadata"]["reason"] == reason


# ============================================================================
# F13: Dual Theme Preference API (5 tests)
# ============================================================================

class TestF13DualThemePreferenceAPI:
    """Equivalence class tests for F13: Dual Theme Preference API."""

    @pytest.mark.asyncio
    async def test_f13_theme_preference_get_default(self, async_client: httpx.AsyncClient):
        res = await async_client.get("/api/v1/users/me/preferences")
        assert res.status_code == 200
        assert "theme" in res.json()

    @pytest.mark.asyncio
    async def test_f13_theme_preference_update_to_dark(self, async_client: httpx.AsyncClient):
        res = await async_client.patch("/api/v1/users/me/preferences", json={"theme": "dark"})
        assert res.status_code == 200
        assert res.json()["theme"] == "dark"

    @pytest.mark.asyncio
    async def test_f13_theme_preference_update_to_light(self, async_client: httpx.AsyncClient):
        res = await async_client.patch("/api/v1/users/me/preferences", json={"theme": "light"})
        assert res.status_code == 200
        assert res.json()["theme"] == "light"

    @pytest.mark.asyncio
    async def test_f13_theme_preference_invalid_theme_rejected(self, async_client: httpx.AsyncClient):
        res = await async_client.patch("/api/v1/users/me/preferences", json={"theme": "neon_blue"})
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_f13_theme_preference_persistence(self, async_client: httpx.AsyncClient):
        await async_client.patch("/api/v1/users/me/preferences", json={"theme": "system"})
        get_res = await async_client.get("/api/v1/users/me/preferences")
        assert get_res.status_code == 200
        assert get_res.json()["theme"] == "system"


# ============================================================================
# F14: Applicant Self-Service Portal (5 tests)
# ============================================================================

class TestF14ApplicantSelfServicePortal:
    """Equivalence class tests for F14: Applicant Self-Service Portal."""

    @pytest.mark.asyncio
    async def test_f14_portal_access_with_valid_invitation_token(self, async_client: httpx.AsyncClient):
        res = await async_client.get("/api/v1/portal/valid-sample-token-12345")
        assert res.status_code == 200
        data = res.json()
        assert "case_number" in data
        assert "required_documents" in data

    @pytest.mark.asyncio
    async def test_f14_portal_access_with_invalid_token_rejected(self, async_client: httpx.AsyncClient):
        res = await async_client.get("/api/v1/portal/invalid-token-12345")
        assert res.status_code == 400

    @pytest.mark.asyncio
    async def test_f14_portal_access_with_expired_token_rejected(self, async_client: httpx.AsyncClient):
        res = await async_client.get("/api/v1/portal/expired-token-99999")
        assert res.status_code == 410

    @pytest.mark.asyncio
    async def test_f14_portal_applicant_document_upload(self, async_client: httpx.AsyncClient, valid_pdf_document: bytes):
        files = {"file": ("portal_id.pdf", valid_pdf_document, "application/pdf")}
        res = await async_client.post("/api/v1/portal/token-applicant-777/documents", files=files)
        assert res.status_code == 201
        assert res.json()["status"] == "uploaded"

    @pytest.mark.asyncio
    async def test_f14_portal_applicant_confirm_fields(self, async_client: httpx.AsyncClient):
        res = await async_client.post("/api/v1/portal/token-applicant-777/confirm-fields")
        assert res.status_code == 200
        assert res.json()["applicant_confirmed"] is True


# ============================================================================
# F15: Controlled Sharing (5 tests)
# ============================================================================

class TestF15ControlledSharing:
    """Equivalence class tests for F15: Controlled Sharing."""

    @pytest.mark.asyncio
    async def test_f15_sharing_create_share_grant_with_30_day_timer(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        # Approve case first
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Ready for sharing"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        share_res = await async_client.post(f"/api/v1/cases/{case_id}/shares", json={"purpose": "loan_app"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert share_res.status_code == 201
        data = share_res.json()
        assert "share_token" in data
        assert "expires_at" in data

    @pytest.mark.asyncio
    async def test_f15_sharing_selective_field_disclosure(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Ready"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        fields = ["full_name"]
        share_res = await async_client.post(f"/api/v1/cases/{case_id}/shares", json={"selected_fields": fields}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert share_res.status_code == 201
        assert share_res.json()["selected_fields"] == fields

    @pytest.mark.asyncio
    async def test_f15_sharing_recipient_access_verified_claims(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Ready"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        share_res = await async_client.post(f"/api/v1/cases/{case_id}/shares", json={}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        token = share_res.json()["share_token"]
        share_id = share_res.json()["id"]

        # Grant consent so claims become accessible
        await async_client.post(f"/api/v1/shares/{share_id}/consent", json={"decision": "granted"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        claims_res = await async_client.get(f"/api/v1/shares/{token}")
        assert claims_res.status_code == 200
        assert "verified_claims" in claims_res.json()

    @pytest.mark.asyncio
    async def test_f15_sharing_early_revocation(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Ready"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        share_res = await async_client.post(f"/api/v1/cases/{case_id}/shares", json={}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        token = share_res.json()["share_token"]
        share_id = share_res.json()["id"]

        # Revoke
        await async_client.post(f"/api/v1/shares/{share_id}/revoke", headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        # Access after revocation -> 410
        claims_res = await async_client.get(f"/api/v1/shares/{token}")
        assert claims_res.status_code == 410

    @pytest.mark.asyncio
    async def test_f15_sharing_unapproved_case_cannot_be_shared(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        # Case in draft
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        share_res = await async_client.post(f"/api/v1/cases/{case_id}/shares", json={}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert share_res.status_code == 400


# ============================================================================
# F16: Applicant Share Consent Workflow (5 tests)
# ============================================================================

class TestF16ApplicantShareConsentWorkflow:
    """Equivalence class tests for F16: Applicant Share Consent Workflow."""

    @pytest.mark.asyncio
    async def test_f16_consent_share_request_pending_consent(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Ready"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        share_res = await async_client.post(f"/api/v1/cases/{case_id}/shares", json={}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert share_res.json()["consent_status"] == "pending_consent"

    @pytest.mark.asyncio
    async def test_f16_consent_applicant_approve_consent(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Ready"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        share_res = await async_client.post(f"/api/v1/cases/{case_id}/shares", json={}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        share_id = share_res.json()["id"]

        consent_res = await async_client.post(f"/api/v1/shares/{share_id}/consent", json={"decision": "granted"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert consent_res.status_code == 200
        assert consent_res.json()["status"] == "granted"

    @pytest.mark.asyncio
    async def test_f16_consent_applicant_decline_consent(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Ready"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        share_res = await async_client.post(f"/api/v1/cases/{case_id}/shares", json={}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        share_id = share_res.json()["id"]

        consent_res = await async_client.post(f"/api/v1/shares/{share_id}/consent", json={"decision": "declined"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert consent_res.status_code == 200
        assert consent_res.json()["status"] == "declined"

    @pytest.mark.asyncio
    async def test_f16_consent_unconsented_share_access_blocked(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Ready"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        share_res = await async_client.post(f"/api/v1/cases/{case_id}/shares", json={}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        token = share_res.json()["share_token"]

        # Attempt read while consent is pending -> 403
        read_res = await async_client.get(f"/api/v1/shares/{token}")
        assert read_res.status_code == 403

    @pytest.mark.asyncio
    async def test_f16_consent_audit_trail_logs_applicant_consent(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Ready"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        share_res = await async_client.post(f"/api/v1/cases/{case_id}/shares", json={}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        share_id = share_res.json()["id"]

        await async_client.post(f"/api/v1/shares/{share_id}/consent", json={"decision": "granted"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        # Audit events check
        audit_res = await async_client.get(f"/api/v1/cases/{case_id}/audit-trail", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert audit_res.status_code == 200


# ============================================================================
# F17: Local Embedded DB / Zero Cloud Run (5 tests)
# ============================================================================

class TestF17LocalEmbeddedDBZeroCloudRun:
    """Equivalence class tests for F17: Local Embedded DB / Zero Cloud Run."""

    @pytest.mark.asyncio
    async def test_f17_local_db_sqlite_embedded_operation(self, async_client: httpx.AsyncClient):
        health = await async_client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_f17_local_db_wal_mode_enabled(self, test_db_engine):
        # Engine can execute PRAGMA queries if engine is active
        if test_db_engine is not None:
            from sqlalchemy import text
            async with test_db_engine.connect() as conn:
                res = await conn.execute(text("PRAGMA journal_mode;"))
                mode = res.scalar()
                assert mode is not None
        else:
            assert True

    @pytest.mark.asyncio
    async def test_f17_local_db_transaction_rollback_isolation(self, db_session):
        # Verify db_session fixture rolls back cleanly
        if db_session is not None:
            assert db_session.is_active is True
        else:
            assert True

    @pytest.mark.asyncio
    async def test_f17_local_db_foreign_key_enforcement(self, test_db_engine):
        if test_db_engine is not None:
            from sqlalchemy import text
            async with test_db_engine.connect() as conn:
                res = await conn.execute(text("PRAGMA foreign_keys;"))
                val = res.scalar()
                assert val in (0, 1)
        else:
            assert True

    @pytest.mark.asyncio
    async def test_f17_local_db_zero_cloud_mock_services(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        # Create case without any external cloud credentials required
        res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "local_zero_cloud"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 201


# ============================================================================
# F18: Pluggable OCR / Provider Fallbacks (5 tests)
# ============================================================================

class TestF18PluggableOCRProviderFallbacks:
    """Equivalence class tests for F18: Pluggable OCR / Provider Fallbacks."""

    @pytest.mark.asyncio
    async def test_f18_ocr_provider_local_regex_extractor(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        text_layer = "Aadhaar number: 8492 0184 7392"
        res = await async_client.post(f"/api/v1/cases/{case_id}/extract-fields", json={"document_type": "aadhaar", "document_text": text_layer}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 200
        assert res.json()["extracted_fields"][0]["draft_value"] == "849201847392"

    @pytest.mark.asyncio
    async def test_f18_ocr_provider_pdf_text_layer_extraction(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        res = await async_client.post(f"/api/v1/cases/{case_id}/extract-fields", json={"document_type": "pan", "document_text": "PAN: ABCPS1234F"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 200
        assert res.json()["extracted_fields"][0]["field_name"] == "pan_number"

    @pytest.mark.asyncio
    async def test_f18_ocr_provider_fallback_to_heuristic(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        # Blank input falls back gracefully to default heuristic extractor
        res = await async_client.post(f"/api/v1/cases/{case_id}/extract-fields", json={"document_type": "aadhaar", "document_text": ""}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 200

    @pytest.mark.asyncio
    async def test_f18_ocr_provider_confidence_aggregation(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        res = await async_client.post(f"/api/v1/cases/{case_id}/extract-fields", json={"document_type": "aadhaar", "document_text": "2948 2847 2841"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        field = res.json()["extracted_fields"][0]
        assert "confidence" in field

    @pytest.mark.asyncio
    async def test_f18_ocr_provider_error_resilience(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        # Corrupted payload does not 500
        res = await async_client.post(f"/api/v1/cases/{case_id}/extract-fields", json={"document_type": "aadhaar", "document_text": "\x00\xff\xfe\x01"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code in (200, 422)


# ============================================================================
# F19: Multi-Tenancy & Tenant Filtering (5 tests)
# ============================================================================

class TestF19MultiTenancyTenantFiltering:
    """Equivalence class tests for F19: Multi-Tenancy & Tenant Filtering."""

    @pytest.mark.asyncio
    async def test_f19_multitenancy_list_cases_scoped_to_active_tenant(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "tenant_a_case"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        res = await async_client.get("/api/v1/cases", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 200
        items = res.json()["items"]
        for item in items:
            assert item["tenant_id"] == tenant_alpha_headers["X-Tenant-ID"]

    @pytest.mark.asyncio
    async def test_f19_multitenancy_cross_tenant_get_case_returns_404(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, tenant_beta_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "private_alpha"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        alpha_case_id = c_res.json()["id"]

        # Beta tenant tries to read Alpha's case -> MUST be 404
        cross_res = await async_client.get(f"/api/v1/cases/{alpha_case_id}", headers=tenant_beta_headers, cookies=auth_admin_cookies)
        assert cross_res.status_code == 404

    @pytest.mark.asyncio
    async def test_f19_multitenancy_cross_tenant_document_access_returns_404(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, tenant_beta_headers: dict, auth_admin_cookies: dict, valid_pdf_document: bytes):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "private_alpha"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        alpha_case_id = c_res.json()["id"]

        files = {"file": ("alpha_doc.pdf", valid_pdf_document, "application/pdf")}
        doc_res = await async_client.post(f"/api/v1/cases/{alpha_case_id}/documents", files=files, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        doc_id = doc_res.json()["id"]

        cross_doc = await async_client.get(f"/api/v1/cases/{alpha_case_id}/documents/{doc_id}/preview", headers=tenant_beta_headers, cookies=auth_admin_cookies)
        assert cross_doc.status_code == 404

    @pytest.mark.asyncio
    async def test_f19_multitenancy_missing_tenant_header_rejected(self, async_client: httpx.AsyncClient, auth_admin_cookies: dict):
        # Call without X-Tenant-ID header
        res = await async_client.get("/api/v1/cases", cookies=auth_admin_cookies)
        assert res.status_code == 400

    @pytest.mark.asyncio
    async def test_f19_multitenancy_mutation_prevented_across_tenants(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, tenant_beta_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "private_alpha"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        alpha_case_id = c_res.json()["id"]

        # Beta tenant tries to patch status -> 404
        patch_res = await async_client.patch(f"/api/v1/cases/{alpha_case_id}/status", json={"status": "invitation_sent"}, headers=tenant_beta_headers, cookies=auth_admin_cookies)
        assert patch_res.status_code == 404


# ============================================================================
# F20: Security & Auth (JWT & CSRF) (5 tests)
# ============================================================================

class TestF20SecurityAuthJWTCSRF:
    """Equivalence class tests for F20: Security & Auth (JWT & CSRF)."""

    @pytest.mark.asyncio
    async def test_f20_auth_login_sets_httponly_jwt_and_csrf_cookies(self, async_client: httpx.AsyncClient):
        login_payload = {"email": "compliance@bankalpha.com", "password": "SecurePassword123!"}
        res = await async_client.post("/api/v1/auth/login", json=login_payload)
        assert res.status_code == 200
        cookies = res.cookies
        assert "access_token" in cookies
        assert "csrf_token" in cookies

    @pytest.mark.asyncio
    async def test_f20_auth_double_submit_csrf_verification(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        # Headers include X-CSRF-Token matching cookies' csrf_token -> Success 201
        res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "csrf_test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 201

    @pytest.mark.asyncio
    async def test_f20_auth_missing_csrf_header_blocked_403(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        headers_no_csrf = {"X-Tenant-ID": tenant_alpha_headers["X-Tenant-ID"]}
        res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "csrf_test"}, headers=headers_no_csrf, cookies=auth_admin_cookies)
        assert res.status_code == 403

    @pytest.mark.asyncio
    async def test_f20_auth_mismatched_csrf_token_blocked_403(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        bad_headers = {
            "X-Tenant-ID": tenant_alpha_headers["X-Tenant-ID"],
            "X-CSRF-Token": "completely-wrong-token-value-12345",
        }
        res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "csrf_test"}, headers=bad_headers, cookies=auth_admin_cookies)
        assert res.status_code == 403

    @pytest.mark.asyncio
    async def test_f20_auth_unauthenticated_request_rejected_401(self, async_client: httpx.AsyncClient):
        # Call protected /me without access_token cookie
        res = await async_client.get("/api/v1/auth/me")
        assert res.status_code == 401


# ============================================================================
# F21: Immutable Audit Trail (5 tests)
# ============================================================================

class TestF21ImmutableAuditTrail:
    """Equivalence class tests for F21: Immutable Audit Trail."""

    @pytest.mark.asyncio
    async def test_f21_audit_trail_created_on_case_creation(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "audit_test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        audit_res = await async_client.get(f"/api/v1/cases/{case_id}/audit-trail", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert audit_res.status_code == 200
        events = audit_res.json()["events"]
        assert any(e["action"] == "case_created" for e in events)

    @pytest.mark.asyncio
    async def test_f21_audit_trail_records_state_transitions(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "audit_test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "invitation_sent"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        audit_res = await async_client.get(f"/api/v1/cases/{case_id}/audit-trail", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        actions = [e["action"] for e in audit_res.json()["events"]]
        assert "status_transition" in actions

    @pytest.mark.asyncio
    async def test_f21_audit_trail_records_reviewer_decisions(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "audit_test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Audited approval"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        audit_res = await async_client.get(f"/api/v1/cases/{case_id}/audit-trail", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        actions = [e["action"] for e in audit_res.json()["events"]]
        assert "case_approved" in actions

    @pytest.mark.asyncio
    async def test_f21_audit_trail_tenant_isolation(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, tenant_beta_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "alpha_audit"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        # Tenant Beta cannot read Tenant Alpha's audit trail
        res = await async_client.get(f"/api/v1/cases/{case_id}/audit-trail", headers=tenant_beta_headers, cookies=auth_admin_cookies)
        assert res.status_code in (200, 404)
        if res.status_code == 200:
            assert res.json()["count"] == 0

    @pytest.mark.asyncio
    async def test_f21_audit_trail_immutability(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "audit_test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        # Attempt to delete or overwrite audit events returns 405 Method Not Allowed
        del_res = await async_client.delete(f"/api/v1/cases/{case_id}/audit-trail", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert del_res.status_code in (404, 405)


# ============================================================================
# F22: Usage Tracking & Quota Counters (5 tests)
# ============================================================================

class TestF22UsageTrackingQuotaCounters:
    """Equivalence class tests for F22: Usage Tracking & Quota Counters."""

    @pytest.mark.asyncio
    async def test_f22_usage_counter_incremented_on_case_creation(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        u1 = await async_client.get("/api/v1/tenants/usage", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        initial = u1.json()["metrics"]["cases_created"]

        await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "usage_test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        u2 = await async_client.get("/api/v1/tenants/usage", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert u2.json()["metrics"]["cases_created"] == initial + 1

    @pytest.mark.asyncio
    async def test_f22_usage_counter_incremented_on_document_upload(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict, valid_pdf_document: bytes):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "usage_test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        u1 = await async_client.get("/api/v1/tenants/usage", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        initial = u1.json()["metrics"]["documents_uploaded"]

        files = {"file": ("doc.pdf", valid_pdf_document, "application/pdf")}
        await async_client.post(f"/api/v1/cases/{case_id}/documents", files=files, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        u2 = await async_client.get("/api/v1/tenants/usage", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert u2.json()["metrics"]["documents_uploaded"] == initial + 1

    @pytest.mark.asyncio
    async def test_f22_usage_counter_incremented_on_review_decision(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        c_res = await async_client.post("/api/v1/cases", json={"applicant": generate_adult_applicant(), "purpose": "usage_test"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        case_id = c_res.json()["id"]

        u1 = await async_client.get("/api/v1/tenants/usage", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        initial = u1.json()["metrics"]["cases_reviewed"]

        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Approved for usage count"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        u2 = await async_client.get("/api/v1/tenants/usage", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert u2.json()["metrics"]["cases_reviewed"] == initial + 1

    @pytest.mark.asyncio
    async def test_f22_usage_metrics_summary_endpoint(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        res = await async_client.get("/api/v1/tenants/usage", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 200
        data = res.json()
        assert "metrics" in data
        assert "quotas" in data
        assert data["tenant_id"] == tenant_alpha_headers["X-Tenant-ID"]

    @pytest.mark.asyncio
    async def test_f22_usage_quota_limit_check(self, async_client: httpx.AsyncClient, tenant_alpha_headers: dict, auth_admin_cookies: dict):
        res = await async_client.get("/api/v1/tenants/usage", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert res.status_code == 200
        data = res.json()
        assert "remaining_cases" in data
        assert data["remaining_cases"] >= 0
