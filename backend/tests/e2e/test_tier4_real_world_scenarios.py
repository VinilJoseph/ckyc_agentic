"""
Tier 4 Real-World Application Scenarios Test Suite for CKYC / eKYC Marketplace MVP.

Contains 5 comprehensive multi-step end-to-end user journeys (43 discrete assertion stages):
- Scenario 1: Happy Path Individual eKYC Onboarding (10 stages)
  Features: F1, F2, F3, F4, F5, F6, F9, F10, F11, F12, F17, F19, F20, F21, F22
- Scenario 2: High-Risk Corporate Director KYC with Discrepancy Correction (9 stages)
  Features: F1, F2, F3, F4, F5, F10, F11, F12, F18, F19, F21, F22
- Scenario 3: Email Intake Auto-Attachment & Unmatched Exception Triage (8 stages)
  Features: F1, F3, F7, F8, F17, F19, F20, F21
- Scenario 4: Fraudulent Identity & Biometric Impersonation Rejection (8 stages)
  Features: F1, F2, F3, F5, F6, F11, F12, F19, F20, F21
- Scenario 5: Controlled Third-Party Credential Sharing with Revocation (8 stages)
  Features: F1, F12, F14, F15, F16, F17, F19, F20, F21
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
# Tier 4: Real-World Application Scenarios
# ============================================================================

class TestTier4RealWorldScenarios:
    """Comprehensive multi-step end-to-end user journeys for CKYC platform."""

    # ------------------------------------------------------------------------
    # Scenario 1: Happy Path Individual eKYC Onboarding (10 Stages)
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_scenario_01_happy_path_individual_ekyc_onboarding(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
        auth_reviewer_cookies: dict,
        valid_pdf_document: bytes,
        matched_biometric_pair: tuple,
    ):
        """
        Scenario 1: Happy Path Individual eKYC Onboarding
        Simulates complete end-to-end onboarding of a retail individual applicant:
        Case Creation -> State Progression -> Document Upload -> OCR Extraction ->
        Algorithmic Validation -> Biometric Matching -> Workspace Inspection ->
        Reviewer Field Confirmation -> Decision Gate Approval -> Audit & Quota Verify.
        """
        # --------------------------------------------------------------------
        # Stage 1: Case Creation & Scoping (F1, F19, F22)
        # --------------------------------------------------------------------
        u_init = await async_client.get("/api/v1/tenants/usage", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        cases_before = u_init.json()["metrics"]["cases_created"]

        applicant = generate_adult_applicant(first_name="Aarav", last_name="Sharma")
        case_payload = {
            "applicant": applicant,
            "purpose": "savings_account_opening",
            "case_type": "individual",
        }
        create_res = await async_client.post(
            "/api/v1/cases",
            json=case_payload,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert create_res.status_code == 201
        case_data = create_res.json()
        case_id = case_data["id"]
        case_number = case_data["case_number"]
        assert case_data["status"] == "draft"
        assert case_data["tenant_id"] == tenant_alpha_headers["X-Tenant-ID"]
        assert case_data["applicant"]["full_name"] == "Aarav Sharma"

        u_after_create = await async_client.get("/api/v1/tenants/usage", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert u_after_create.json()["metrics"]["cases_created"] == cases_before + 1

        # --------------------------------------------------------------------
        # Stage 2: Stepper & State Progression (F2, F9)
        # --------------------------------------------------------------------
        # Transition: draft -> invitation_sent
        s1 = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "invitation_sent"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert s1.status_code == 200
        assert s1.json()["status"] == "invitation_sent"
        assert s1.json()["stepper"]["current_stage"] == "invitation_sent"

        # Transition: invitation_sent -> awaiting_documents
        s2 = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "awaiting_documents"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert s2.status_code == 200
        assert s2.json()["status"] == "awaiting_documents"
        assert len(s2.json()["stepper"]["completed_steps"]) >= 2

        # --------------------------------------------------------------------
        # Stage 3: Secure Document Upload (F3)
        # --------------------------------------------------------------------
        files = {"file": ("aadhaar_front_back.pdf", valid_pdf_document, "application/pdf")}
        data = {"document_type": "identity_card"}
        upload_res = await async_client.post(
            f"/api/v1/cases/{case_id}/documents",
            files=files,
            data=data,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert upload_res.status_code == 201
        doc_data = upload_res.json()
        doc_id = doc_data["id"]
        assert doc_data["mime_type"] == "application/pdf"
        assert doc_data["file_hash"] == hashlib.sha256(valid_pdf_document).hexdigest()

        # Advance status: awaiting_documents -> documents_received
        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "documents_received"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )

        # --------------------------------------------------------------------
        # Stage 4: Automated Field Extraction (F4)
        # --------------------------------------------------------------------
        ocr_text = (
            f"GOVERNMENT OF INDIA Aarav Sharma DOB: {applicant['date_of_birth']} "
            f"Aadhaar Number: {applicant['aadhaar_number'][:4]} {applicant['aadhaar_number'][4:8]} {applicant['aadhaar_number'][8:]}"
        )
        ocr_res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "aadhaar", "document_text": ocr_text},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert ocr_res.status_code == 200
        extracted_fields = ocr_res.json()["extracted_fields"]
        assert len(extracted_fields) >= 1
        aadhaar_field = extracted_fields[0]
        assert aadhaar_field["field_name"] == "aadhaar_number"
        assert aadhaar_field["draft_value"] == applicant["aadhaar_number"]
        assert aadhaar_field["confidence"] >= 0.90
        field_id = aadhaar_field["id"]

        # --------------------------------------------------------------------
        # Stage 5: KYC Criteria Validation (F5)
        # --------------------------------------------------------------------
        val_res = await async_client.post(
            f"/api/v1/cases/{case_id}/validate",
            json={
                "aadhaar_number": aadhaar_field["draft_value"],
                "date_of_birth": applicant["date_of_birth"],
            },
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert val_res.status_code == 200
        val_data = val_res.json()
        assert val_data["is_valid"] is True
        assert len(val_data["issues"]) == 0

        # --------------------------------------------------------------------
        # Stage 6: Biometric Facial Comparison (F6)
        # --------------------------------------------------------------------
        selfie_bytes, id_crop_bytes = matched_biometric_pair
        bio_files = {
            "selfie": ("applicant_selfie.png", selfie_bytes, "image/png"),
            "id_photo": ("aadhaar_photo.png", id_crop_bytes, "image/png"),
        }
        bio_res = await async_client.post(
            f"/api/v1/cases/{case_id}/selfie-match",
            files=bio_files,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert bio_res.status_code == 200
        bio_data = bio_res.json()
        assert bio_data["is_match"] is True
        assert bio_data["confidence"] >= 0.75

        # --------------------------------------------------------------------
        # Stage 7: Split Reviewer Workspace Inspection (F10)
        # --------------------------------------------------------------------
        # Transition: documents_received -> in_review
        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "in_review"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )

        ws_res = await async_client.get(
            f"/api/v1/cases/{case_id}",
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert ws_res.status_code == 200
        ws_data = ws_res.json()
        assert len(ws_data["documents"]) == 1
        assert len(ws_data["extracted_fields"]) >= 1
        assert ws_data["selfie_match"]["is_match"] is True
        assert len(ws_data["validation_issues"]) == 0

        # --------------------------------------------------------------------
        # Stage 8: Reviewer Field Confirmation (F11, F21)
        # --------------------------------------------------------------------
        confirm_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/fields/{field_id}",
            json={"reviewer_decision": "confirmed", "reviewer_notes": "Aadhaar number matches uploaded document"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert confirm_res.status_code == 200
        assert confirm_res.json()["reviewer_decision"] == "confirmed"
        assert confirm_res.json()["confirmed_value"] == applicant["aadhaar_number"]

        # --------------------------------------------------------------------
        # Stage 9: Case Approval Decision Gate (F12, F2, F21)
        # --------------------------------------------------------------------
        justification = "Applicant identity verified against valid Aadhaar card and high biometric confidence (0.85+)."
        approval_res = await async_client.post(
            f"/api/v1/cases/{case_id}/approve",
            json={"reason": justification},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert approval_res.status_code == 200
        assert approval_res.json()["status"] == "approved"
        assert approval_res.json()["reason"] == justification

        # Verify case is terminal
        final_case = await async_client.get(f"/api/v1/cases/{case_id}", headers=tenant_alpha_headers, cookies=auth_reviewer_cookies)
        assert final_case.json()["status"] == "approved"

        # --------------------------------------------------------------------
        # Stage 10: Usage Metrics & Audit Trail Verification (F21, F22)
        # --------------------------------------------------------------------
        # Audit trail check
        audit_res = await async_client.get(f"/api/v1/cases/{case_id}/audit-trail", headers=tenant_alpha_headers, cookies=auth_reviewer_cookies)
        assert audit_res.status_code == 200
        events = audit_res.json()["events"]
        actions = [e["action"] for e in events]
        assert "case_created" in actions
        assert "document_uploaded" in actions
        assert "status_transition" in actions
        assert "field_decision" in actions
        assert "case_approved" in actions

        # Quota metrics check
        u_final = await async_client.get("/api/v1/tenants/usage", headers=tenant_alpha_headers, cookies=auth_reviewer_cookies)
        assert u_final.json()["metrics"]["cases_reviewed"] >= 1
        assert u_final.json()["metrics"]["documents_uploaded"] >= 1

    # ------------------------------------------------------------------------
    # Scenario 2: High-Risk Corporate Director KYC with Discrepancy Correction (9 Stages)
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_scenario_02_corporate_director_kyc_with_discrepancy_correction(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
        auth_reviewer_cookies: dict,
        valid_pdf_document: bytes,
    ):
        """
        Scenario 2: High-Risk Corporate Director KYC with Discrepancy Correction
        Simulates merchant onboarding for a business entity where OCR extracts an
        erroneous PAN entity type ('P' instead of 'C'), the validation engine flags
        the rule violation, the reviewer manually edits the field with audit reason,
        and the case reaches final approval.
        """
        # --------------------------------------------------------------------
        # Stage 1: Corporate Case Initialization (F1, F19)
        # --------------------------------------------------------------------
        corp = generate_corporate_entity(company_name="Apex Logistics Pvt Ltd")
        corp_payload = {
            "applicant": corp,
            "purpose": "corporate_merchant_onboarding",
            "case_type": "business",
        }
        create_res = await async_client.post(
            "/api/v1/cases",
            json=corp_payload,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert create_res.status_code == 201
        case_id = create_res.json()["id"]
        assert create_res.json()["case_type"] == "business"
        assert create_res.json()["applicant"]["business_name"] == "Apex Logistics Pvt Ltd"

        # --------------------------------------------------------------------
        # Stage 2: State Progression to Documents Received (F2)
        # --------------------------------------------------------------------
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "awaiting_documents"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        # --------------------------------------------------------------------
        # Stage 3: Corporate Document Submission (F3)
        # --------------------------------------------------------------------
        files = {"file": ("certificate_of_incorporation.pdf", valid_pdf_document, "application/pdf")}
        doc_res = await async_client.post(
            f"/api/v1/cases/{case_id}/documents",
            files=files,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert doc_res.status_code == 201
        assert doc_res.json()["mime_type"] == "application/pdf"

        # --------------------------------------------------------------------
        # Stage 4: OCR Extraction with Typo / Erroneous PAN (F4, F18)
        # --------------------------------------------------------------------
        # Simulate OCR reading corrupted PAN with individual 'P' instead of corporate 'C' or invalid 4th char
        corrupted_pan = generate_invalid_pan(reason="entity")
        ocr_res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "pan", "document_text": f"INCOME TAX DEPARTMENT PAN: {corrupted_pan}"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert ocr_res.status_code == 200
        field_id = ocr_res.json()["extracted_fields"][0]["id"]
        assert ocr_res.json()["extracted_fields"][0]["draft_value"] == corrupted_pan

        # --------------------------------------------------------------------
        # Stage 5: Algorithmic Criteria Validation Discrepancy Flagging (F5)
        # --------------------------------------------------------------------
        val_res = await async_client.post(
            f"/api/v1/cases/{case_id}/validate",
            json={"pan_number": corrupted_pan},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert val_res.status_code == 200
        assert val_res.json()["is_valid"] is False
        issues = val_res.json()["issues"]
        assert any(i["code"] == "INVALID_PAN_ENTITY_TYPE" for i in issues)

        # --------------------------------------------------------------------
        # Stage 6: Split Workspace Discrepancy Inspection (F10)
        # --------------------------------------------------------------------
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "in_review"}, headers=tenant_alpha_headers, cookies=auth_reviewer_cookies)

        ws_res = await async_client.get(f"/api/v1/cases/{case_id}", headers=tenant_alpha_headers, cookies=auth_reviewer_cookies)
        assert ws_res.status_code == 200
        assert len(ws_res.json()["validation_issues"]) >= 1

        # --------------------------------------------------------------------
        # Stage 7: Reviewer Manual Field Correction (F11, F21)
        # --------------------------------------------------------------------
        correct_corporate_pan = corp["pan_number"]  # Valid corporate PAN ('C')
        correction_notes = "Corrected 4th character from blurred OCR scan to match Certificate of Incorporation"
        patch_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/fields/{field_id}",
            json={
                "reviewer_decision": "corrected",
                "corrected_value": correct_corporate_pan,
                "reviewer_notes": correction_notes,
            },
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["confirmed_value"] == correct_corporate_pan
        assert patch_res.json()["reviewer_notes"] == correction_notes

        # --------------------------------------------------------------------
        # Stage 8: Re-Validation Clearance (F5)
        # --------------------------------------------------------------------
        reval_res = await async_client.post(
            f"/api/v1/cases/{case_id}/validate",
            json={"pan_number": correct_corporate_pan},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert reval_res.status_code == 200
        assert reval_res.json()["is_valid"] is True
        assert len(reval_res.json()["issues"]) == 0

        # --------------------------------------------------------------------
        # Stage 9: Mandatory Written Decision & Case Approval (F12, F21, F22)
        # --------------------------------------------------------------------
        corp_approval_reason = f"Corporate entity PAN verified against MCA database. {correction_notes}."
        approve_res = await async_client.post(
            f"/api/v1/cases/{case_id}/approve",
            json={"reason": corp_approval_reason},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert approve_res.status_code == 200
        assert approve_res.json()["status"] == "approved"

        # Verify audit trail
        audit_res = await async_client.get(f"/api/v1/cases/{case_id}/audit-trail", headers=tenant_alpha_headers, cookies=auth_reviewer_cookies)
        assert any(e["action"] == "case_approved" for e in audit_res.json()["events"])

    # ------------------------------------------------------------------------
    # Scenario 3: Email Intake Auto-Attachment & Unmatched Exception Triage (8 Stages)
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_scenario_03_email_intake_auto_attachment_and_exception_triage(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        auth_admin_cookies: dict,
        unmatched_intake_eml: bytes,
    ):
        """
        Scenario 3: Email Intake Auto-Attachment & Unmatched Exception Triage
        Flow:
        Part A: Inbound email with subject reference [CASE-XXXX] auto-attaches to Case 1001.
        Part B: Inbound email without valid reference routes to Exception Queue;
        Compliance Officer reviews, triages, and manually assigns to Case 1002.
        Cross-tenant isolation in exception queue is enforced.
        """
        # --------------------------------------------------------------------
        # Stage 1: Case Setup for Auto-Attachment (F1, F19)
        # --------------------------------------------------------------------
        c1 = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "email_auto_attach"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case1_id = c1.json()["id"]
        case1_number = c1.json()["case_number"]

        # Advance to awaiting_documents
        await async_client.patch(f"/api/v1/cases/{case1_id}/status", json={"status": "awaiting_documents"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        # --------------------------------------------------------------------
        # Stage 2: Matched Inbound Email Submission (F7)
        # --------------------------------------------------------------------
        eml_bytes = generate_synthetic_eml(case_number=case1_number)
        files = {"file": ("submission.eml", eml_bytes, "message/rfc822")}
        intake_res = await async_client.post("/api/v1/intake/eml", files=files, headers=tenant_alpha_headers)
        assert intake_res.status_code == 200
        intake_data = intake_res.json()
        assert intake_data["status"] == "attached_to_case"
        assert intake_data["case_number"] == case1_number
        assert intake_data["attachments_count"] == 2

        # --------------------------------------------------------------------
        # Stage 3: Automated Attachment & Status Update (F7, F3)
        # --------------------------------------------------------------------
        case1_detail = await async_client.get(f"/api/v1/cases/{case1_id}", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert case1_detail.json()["status"] == "documents_received"
        assert len(case1_detail.json()["documents"]) == 2

        # --------------------------------------------------------------------
        # Stage 4: Unmatched Inbound Email Submission (F7, F8)
        # --------------------------------------------------------------------
        files_unmatched = {"file": ("lost_submission.eml", unmatched_intake_eml, "message/rfc822")}
        unmatched_res = await async_client.post("/api/v1/intake/eml", files=files_unmatched, headers=tenant_alpha_headers)
        assert unmatched_res.status_code == 200
        unmatched_data = unmatched_res.json()
        assert unmatched_data["status"] == "routed_to_exception_queue"
        exc_id = unmatched_data["exception_id"]

        # --------------------------------------------------------------------
        # Stage 5: Email Exception Queue Inspection (F8)
        # --------------------------------------------------------------------
        q_res = await async_client.get("/api/v1/email/exceptions", headers=tenant_alpha_headers)
        assert q_res.status_code == 200
        items = q_res.json()["items"]
        assert any(e["id"] == exc_id for e in items)

        # --------------------------------------------------------------------
        # Stage 6: Case Setup for Manual Assignment (F1)
        # --------------------------------------------------------------------
        c2 = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "manual_triage_target"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case2_id = c2.json()["id"]

        # --------------------------------------------------------------------
        # Stage 7: Manual Triage & Case Assignment (F8, F3)
        # --------------------------------------------------------------------
        assign_res = await async_client.post(
            f"/api/v1/email/exceptions/{exc_id}/assign",
            json={"case_id": case2_id},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert assign_res.status_code == 200
        assert assign_res.json()["status"] == "assigned"

        case2_detail = await async_client.get(f"/api/v1/cases/{case2_id}", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert case2_detail.json()["status"] == "documents_received"

        # --------------------------------------------------------------------
        # Stage 8: Cross-Tenant Isolation in Exception Queue (F8, F19)
        # --------------------------------------------------------------------
        beta_queue = await async_client.get("/api/v1/email/exceptions", headers=tenant_beta_headers)
        assert beta_queue.status_code == 200
        assert not any(e["id"] == exc_id for e in beta_queue.json()["items"])

    # ------------------------------------------------------------------------
    # Scenario 4: Fraudulent Identity & Biometric Impersonation Rejection (8 Stages)
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_scenario_04_fraudulent_identity_and_biometric_rejection(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
        auth_reviewer_cookies: dict,
        valid_pdf_document: bytes,
        mismatched_biometric_pair: tuple,
    ):
        """
        Scenario 4: Fraudulent Identity & Biometric Impersonation Rejection
        Simulates an adversarial fraud attempt:
        Invalid Aadhaar Verhoeff checksum + mismatched selfie impersonator.
        Validator flags invalid Aadhaar, biometrics returns mismatch (<0.40).
        Reviewer marks field rejected, enters mandatory fraud reason, and transitions case to rejected.
        """
        # --------------------------------------------------------------------
        # Stage 1: Case Creation for Fraud Test (F1, F19)
        # --------------------------------------------------------------------
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "adversarial_fraud_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c_res.json()["id"]

        # --------------------------------------------------------------------
        # Stage 2: Fraudulent Document Upload (F3)
        # --------------------------------------------------------------------
        files = {"file": ("forged_id.pdf", valid_pdf_document, "application/pdf")}
        await async_client.post(f"/api/v1/cases/{case_id}/documents", files=files, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        # --------------------------------------------------------------------
        # Stage 3: Algorithmic Fraud Detection via Verhoeff Failure (F5)
        # --------------------------------------------------------------------
        fake_aadhaar = generate_invalid_aadhaar()
        val_res = await async_client.post(
            f"/api/v1/cases/{case_id}/validate",
            json={"aadhaar_number": fake_aadhaar},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert val_res.status_code == 200
        assert val_res.json()["is_valid"] is False
        assert any(i["code"] == "INVALID_VERHOEFF_CHECKSUM" for i in val_res.json()["issues"])

        # --------------------------------------------------------------------
        # Stage 4: Biometric Impersonation Check (F6)
        # --------------------------------------------------------------------
        selfie_bytes, impostor_bytes = mismatched_biometric_pair
        bio_files = {
            "selfie": ("applicant_selfie.png", selfie_bytes, "image/png"),
            "id_photo": ("impostor_doc_photo.png", impostor_bytes, "image/png"),
        }
        bio_res = await async_client.post(
            f"/api/v1/cases/{case_id}/selfie-match",
            files=bio_files,
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert bio_res.status_code == 200
        assert bio_res.json()["is_match"] is False
        assert bio_res.json()["confidence"] < 0.40

        # --------------------------------------------------------------------
        # Stage 5: Split Workspace Reviewer Alert (F10)
        # --------------------------------------------------------------------
        # Advance to in_review
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "awaiting_documents"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "documents_received"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        await async_client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "in_review"}, headers=tenant_alpha_headers, cookies=auth_reviewer_cookies)

        ws = await async_client.get(f"/api/v1/cases/{case_id}", headers=tenant_alpha_headers, cookies=auth_reviewer_cookies)
        assert ws.status_code == 200
        assert len(ws.json()["validation_issues"]) >= 1
        assert ws.json()["selfie_match"]["is_match"] is False

        # --------------------------------------------------------------------
        # Stage 6: Reviewer Marks Flagged Field as Rejected (F11)
        # --------------------------------------------------------------------
        ocr_res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "aadhaar", "document_text": f"Aadhaar {fake_aadhaar}"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        field_id = ocr_res.json()["extracted_fields"][0]["id"]

        reject_field_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/fields/{field_id}",
            json={
                "reviewer_decision": "rejected",
                "reviewer_notes": "Aadhaar checksum failed D5 Verhoeff verification and face did not match selfie",
            },
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert reject_field_res.status_code == 200
        assert reject_field_res.json()["reviewer_decision"] == "rejected"

        # --------------------------------------------------------------------
        # Stage 7: Final Case Rejection with Mandatory Reason (F12)
        # --------------------------------------------------------------------
        fraud_rejection_reason = "FRAUD_ALERT: Impersonation detected with forged Aadhaar and mismatched selfie."
        rej_res = await async_client.post(
            f"/api/v1/cases/{case_id}/reject",
            json={"reason": fraud_rejection_reason},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert rej_res.status_code == 200
        assert rej_res.json()["status"] == "rejected"
        assert rej_res.json()["reason"] == fraud_rejection_reason

        # --------------------------------------------------------------------
        # Stage 8: Terminal State Lock & Audit Trail Verification (F2, F21)
        # --------------------------------------------------------------------
        # Lock enforcement
        illegal_reopen = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "in_review"},
            headers=tenant_alpha_headers,
            cookies=auth_reviewer_cookies,
        )
        assert illegal_reopen.status_code in (400, 422)

        # Audit trail checks
        audit = await async_client.get(f"/api/v1/cases/{case_id}/audit-trail", headers=tenant_alpha_headers, cookies=auth_reviewer_cookies)
        events = audit.json()["events"]
        assert any(e["action"] == "case_rejected" and e["metadata"]["reason"] == fraud_rejection_reason for e in events)

    # ------------------------------------------------------------------------
    # Scenario 5: Controlled Third-Party Credential Sharing with Revocation (8 Stages)
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_scenario_05_controlled_credential_sharing_with_revocation(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        auth_admin_cookies: dict,
        auth_applicant_cookies: dict,
    ):
        """
        Scenario 5: Controlled Third-Party Credential Sharing with Revocation
        Flow:
        Approved KYC case recipient requests to share KYC package with 3rd-party bank.
        30-day token generated. Pre-consent access is blocked.
        Applicant grants consent. 3rd-party accesses verified claims.
        Applicant revokes access early; subsequent access returns 410 Gone.
        """
        # --------------------------------------------------------------------
        # Stage 1: Approved KYC Case Establishment (F1, F2, F12)
        # --------------------------------------------------------------------
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "third_party_syndication"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c_res.json()["id"]

        await async_client.post(
            f"/api/v1/cases/{case_id}/approve",
            json={"reason": "KYC Verified and approved for banking partner syndication"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )

        # --------------------------------------------------------------------
        # Stage 2: Share Grant Generation (F15)
        # --------------------------------------------------------------------
        share_payload = {
            "recipient_tenant_id": tenant_beta_headers["X-Tenant-ID"],
            "purpose": "syndicated_loan_underwriting",
            "selected_fields": ["full_name", "date_of_birth"],
        }
        share_res = await async_client.post(
            f"/api/v1/cases/{case_id}/shares",
            json=share_payload,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert share_res.status_code == 201
        share_data = share_res.json()
        share_token = share_data["share_token"]
        share_id = share_data["id"]
        assert share_data["consent_status"] == "pending_consent"
        assert "expires_at" in share_data

        # --------------------------------------------------------------------
        # Stage 3: Pre-Consent Block Enforcement (F15, F16)
        # --------------------------------------------------------------------
        # Third party tries to access before consent
        pre_consent_get = await async_client.get(f"/api/v1/shares/{share_token}")
        assert pre_consent_get.status_code == 403

        # --------------------------------------------------------------------
        # Stage 4: Applicant Consent Approval (F16, F21)
        # --------------------------------------------------------------------
        consent_res = await async_client.post(
            f"/api/v1/shares/{share_id}/consent",
            json={"decision": "granted"},
            headers=tenant_alpha_headers,
            cookies=auth_applicant_cookies,
        )
        assert consent_res.status_code == 200
        assert consent_res.json()["status"] == "granted"

        # --------------------------------------------------------------------
        # Stage 5: Authorized Third-Party Access (F15)
        # --------------------------------------------------------------------
        claims_res = await async_client.get(f"/api/v1/shares/{share_token}")
        assert claims_res.status_code == 200
        claims_data = claims_res.json()
        assert "verified_claims" in claims_data
        assert claims_data["verified_claims"]["status"] == "verified"
        assert "expires_at" in claims_data

        # --------------------------------------------------------------------
        # Stage 6: Early Revocation by User (F15, F21)
        # --------------------------------------------------------------------
        revoke_res = await async_client.post(
            f"/api/v1/shares/{share_id}/revoke",
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert revoke_res.status_code == 200
        assert revoke_res.json()["status"] == "revoked"

        # --------------------------------------------------------------------
        # Stage 7: Post-Revocation Access Denial (F15)
        # --------------------------------------------------------------------
        post_revoke_get = await async_client.get(f"/api/v1/shares/{share_token}")
        assert post_revoke_get.status_code == 410

        # --------------------------------------------------------------------
        # Stage 8: End-to-End Audit Trail Verification (F21)
        # --------------------------------------------------------------------
        audit_res = await async_client.get(f"/api/v1/cases/{case_id}/audit-trail", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert audit_res.status_code == 200
        events = audit_res.json()["events"]
        assert len(events) >= 1
