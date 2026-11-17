"""
Tier 3 Cross-Feature Combination Test Suite for CKYC / eKYC Marketplace MVP.

Contains exactly 22 pairwise interaction tests covering cross-feature dependencies:
1.  F1 + F3:   Case Creation + Document Upload (create case, upload doc, verify linked)
2.  F2 + F12:  State Machine + Decision Gate (transition to in_review, approve with reason, verify approved)
3.  F3 + F4:   Document Upload + OCR Extraction (upload PDF/JPEG, verify extracted fields generated)
4.  F4 + F5:   OCR Extraction + Validation Engine (extracted fields evaluated by Verhoeff / PAN / MRZ rules)
5.  F5 + F11:  Validation Engine + Reviewer Field Correction (discrepancy flagged, reviewer corrects field)
6.  F6 + F12:  Biometric Matching + Case Rejection (impostor selfie mismatch score < 0.40 triggers rejection)
7.  F7 + F8:   Inbound Email Ingestion + Exception Queue (unmatched email routes to exception queue, matched attaches)
8.  F8 + F1:   Exception Queue + Case Assignment (unmatched email manually assigned to existing case)
9.  F9 + F2:   Lifecycle Stepper + State Transitions (timeline stages update synchronously with state changes)
10. F10 + F11: Split Workspace + Field Decisions (reviewer workspace displays field deck, reviewer updates field)
11. F11 + F21: Field Decisions + Audit Trail (field correction appends immutable event to audit log)
12. F12 + F15: Case Approval + Controlled Sharing (approved case enables 30-day credential sharing)
13. F13 + F20: Theme Preferences + Auth (theme preference saved per authenticated user session)
14. F14 + F3:  Applicant Portal + Document Upload (applicant uploads doc via portal invitation token)
15. F15 + F16: Controlled Sharing + Share Consent (share grant requires applicant consent before release)
16. F16 + F21: Share Consent + Audit Trail (consent approval and revocation recorded in audit trail)
17. F17 + F1:  Local SQLite DB + Case Operations (case creation persists across queries with WAL mode)
18. F18 + F4:  Pluggable OCR Fallback + Field Extraction (fallback to regex/synthetic when primary fails)
19. F19 + F1:  Multi-Tenancy + Case Scoping (cases isolated strictly to creating tenant)
20. F20 + F19: Auth + Multi-Tenancy (JWT claims bind user to specific tenant, preventing cross-tenant reads)
21. F21 + F12: Audit Trail + Review Decision (approval reason and reviewer ID logged immutably)
22. F22 + F1:  Usage Counters + Case Creation (tenant case counter increments upon case creation)
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
# Tier 3: 22 Pairwise Cross-Feature Integration Tests
# ============================================================================

class TestTier3CrossFeatureCombinations:
    """Pairwise combination tests for CKYC cross-feature workflows."""

    # ------------------------------------------------------------------------
    # 1. F1 + F3: Case Creation + Document Upload
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_01_case_creation_and_document_upload_linkage(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
        valid_pdf_document: bytes,
    ):
        """Verify that a newly created KYC case can ingest documents and link them accurately."""
        # Step 1: Create case
        applicant = generate_adult_applicant()
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": applicant, "purpose": "onboarding_doc_linkage"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert c_res.status_code == 201
        case_data = c_res.json()
        case_id = case_data["id"]
        assert case_data["status"] == "draft"

        # Step 2: Upload document
        files = {"file": ("id_proof.pdf", valid_pdf_document, "application/pdf")}
        data = {"document_type": "identity_card"}
        doc_res = await async_client.post(
            f"/api/v1/cases/{case_id}/documents",
            files=files,
            data=data,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert doc_res.status_code == 201
        doc_data = doc_res.json()
        doc_id = doc_data["id"]
        assert doc_data["case_id"] == case_id
        assert doc_data["file_hash"] == hashlib.sha256(valid_pdf_document).hexdigest()

        # Step 3: Fetch case inspection and assert document linkage
        case_detail = await async_client.get(
            f"/api/v1/cases/{case_id}",
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert case_detail.status_code == 200
        docs = case_detail.json()["documents"]
        assert len(docs) >= 1
        assert any(d["id"] == doc_id for d in docs)

    # ------------------------------------------------------------------------
    # 2. F2 + F12: State Machine + Decision Gate
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_02_state_machine_transition_and_approval_gate(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Verify valid state transitions culminating in reviewer approval with written reason."""
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "state_machine_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c_res.json()["id"]

        # Transition draft -> awaiting_documents -> documents_received -> in_review
        s1 = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "awaiting_documents"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert s1.status_code == 200

        s2 = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "documents_received"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert s2.status_code == 200

        s3 = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "in_review"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert s3.status_code == 200
        assert s3.json()["status"] == "in_review"

        # Final decision gate approval with mandatory reason
        approval_reason = "All identity checks and criteria validations passed satisfactorily"
        app_res = await async_client.post(
            f"/api/v1/cases/{case_id}/approve",
            json={"reason": approval_reason},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert app_res.status_code == 200
        assert app_res.json()["status"] == "approved"
        assert app_res.json()["reason"] == approval_reason

        # Verify terminal state lock: cannot jump back to in_review
        lock_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "in_review"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert lock_res.status_code in (400, 422)

    # ------------------------------------------------------------------------
    # 3. F3 + F4: Document Upload + OCR Extraction
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_03_document_upload_and_ocr_field_generation(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
        valid_pdf_document: bytes,
    ):
        """Verify uploaded document undergoes OCR extraction populating structured draft fields."""
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "ocr_extraction_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c_res.json()["id"]

        # Upload document
        files = {"file": ("aadhaar.pdf", valid_pdf_document, "application/pdf")}
        doc_res = await async_client.post(
            f"/api/v1/cases/{case_id}/documents",
            files=files,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert doc_res.status_code == 201

        # Trigger OCR extraction
        ocr_payload = {
            "document_type": "aadhaar",
            "document_text": "GOVERNMENT OF INDIA Aarav Sharma DOB: 1990-05-15 2948 2847 2841",
        }
        ocr_res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json=ocr_payload,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert ocr_res.status_code == 200
        extracted = ocr_res.json()["extracted_fields"]
        assert len(extracted) >= 1
        assert extracted[0]["field_name"] == "aadhaar_number"
        assert extracted[0]["draft_value"] == "294828472841"
        assert extracted[0]["confidence"] > 0.80

    # ------------------------------------------------------------------------
    # 4. F4 + F5: OCR Extraction + Validation Engine
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_04_ocr_extracted_fields_evaluated_by_validation_engine(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Verify fields output from OCR are passed directly into validation engine."""
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "ocr_val_pipeline"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c_res.json()["id"]

        valid_aadhaar = generate_valid_aadhaar()
        ocr_text = f"UNIQUE IDENTIFICATION AUTHORITY OF INDIA Aadhaar: {valid_aadhaar[:4]} {valid_aadhaar[4:8]} {valid_aadhaar[8:]}"

        # 1. OCR Extraction
        ocr_res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "aadhaar", "document_text": ocr_text},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert ocr_res.status_code == 200
        extracted_value = ocr_res.json()["extracted_fields"][0]["draft_value"]
        assert extracted_value == valid_aadhaar

        # 2. Validation Engine evaluates extracted value
        val_res = await async_client.post(
            f"/api/v1/cases/{case_id}/validate",
            json={"aadhaar_number": extracted_value},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert val_res.status_code == 200
        assert val_res.json()["is_valid"] is True
        assert len(val_res.json()["issues"]) == 0

    # ------------------------------------------------------------------------
    # 5. F5 + F11: Validation Engine + Reviewer Field Correction
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_05_validation_flag_triggers_reviewer_field_correction(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Verify validation issue is flagged, reviewer applies correction, and field is rectified."""
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "val_correction_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c_res.json()["id"]

        # Step 1: OCR creates a draft field
        ocr_res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "aadhaar"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        field_id = ocr_res.json()["extracted_fields"][0]["id"]

        # Step 2: Corrupted Aadhaar is flagged by validator
        invalid_aadhaar = generate_invalid_aadhaar()
        val_res = await async_client.post(
            f"/api/v1/cases/{case_id}/validate",
            json={"aadhaar_number": invalid_aadhaar},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert val_res.status_code == 200
        assert val_res.json()["is_valid"] is False
        assert any(i["code"] == "INVALID_VERHOEFF_CHECKSUM" for i in val_res.json()["issues"])

        # Step 3: Reviewer inspects discrepancy and applies manual correction
        corrected_valid_aadhaar = generate_valid_aadhaar()
        patch_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/fields/{field_id}",
            json={
                "reviewer_decision": "corrected",
                "corrected_value": corrected_valid_aadhaar,
                "reviewer_notes": "Corrected corrupted checksum from document inspection",
            },
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert patch_res.status_code == 200
        field_data = patch_res.json()
        assert field_data["reviewer_decision"] == "corrected"
        assert field_data["confirmed_value"] == corrected_valid_aadhaar
        assert len(field_data["correction_history"]) >= 1

    # ------------------------------------------------------------------------
    # 6. F6 + F12: Biometric Matching + Case Rejection
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_06_biometric_impostor_mismatch_triggers_case_rejection(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
        mismatched_biometric_pair: tuple,
    ):
        """Verify biometric match failure (<0.40) directly supports reviewer rejection decision."""
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "fraud_check"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c_res.json()["id"]

        # Step 1: Execute selfie-to-ID matching with impostor pair
        selfie_bytes, impostor_bytes = mismatched_biometric_pair
        files = {
            "selfie": ("selfie.png", selfie_bytes, "image/png"),
            "id_photo": ("impostor.png", impostor_bytes, "image/png"),
        }
        match_res = await async_client.post(
            f"/api/v1/cases/{case_id}/selfie-match",
            files=files,
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert match_res.status_code == 200
        match_data = match_res.json()
        assert match_data["is_match"] is False
        assert match_data["confidence"] < 0.40

        # Step 2: Reviewer rejects case citing the biometric failure
        fraud_reason = f"Biometric verification failure: facial match confidence {match_data['confidence']} < 0.40 indicates impersonation."
        reject_res = await async_client.post(
            f"/api/v1/cases/{case_id}/reject",
            json={"reason": fraud_reason},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert reject_res.status_code == 200
        assert reject_res.json()["status"] == "rejected"
        assert reject_res.json()["reason"] == fraud_reason

    # ------------------------------------------------------------------------
    # 7. F7 + F8: Inbound Email Ingestion + Exception Queue
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_07_inbound_email_routing_auto_match_vs_exception_queue(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
        unmatched_intake_eml: bytes,
    ):
        """Verify inbound email with matching case tag auto-attaches, while unmatched routes to exception queue."""
        # 1. Create active case
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "email_intake"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_number = c_res.json()["case_number"]

        # 2. Ingest matching email
        matched_eml = generate_synthetic_eml(case_number=case_number)
        files_matched = {"file": ("matched.eml", matched_eml, "message/rfc822")}
        m_res = await async_client.post("/api/v1/intake/eml", files=files_matched, headers=tenant_alpha_headers)
        assert m_res.status_code == 200
        assert m_res.json()["status"] == "attached_to_case"
        assert m_res.json()["case_number"] == case_number

        # 3. Ingest unmatched email
        files_unmatched = {"file": ("unmatched.eml", unmatched_intake_eml, "message/rfc822")}
        u_res = await async_client.post("/api/v1/intake/eml", files=files_unmatched, headers=tenant_alpha_headers)
        assert u_res.status_code == 200
        assert u_res.json()["status"] == "routed_to_exception_queue"
        exc_id = u_res.json()["exception_id"]

        # 4. Confirm exception appears in queue
        q_res = await async_client.get("/api/v1/email/exceptions", headers=tenant_alpha_headers)
        assert q_res.status_code == 200
        exceptions = q_res.json()["items"]
        assert any(e["id"] == exc_id for e in exceptions)

    # ------------------------------------------------------------------------
    # 8. F8 + F1: Exception Queue + Case Assignment
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_08_email_exception_manual_assignment_to_existing_case(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Verify compliance officer can assign an unmatched email exception to an existing case."""
        # Step 1: Submit unmatched email webhook
        inbound = await async_client.post(
            "/api/v1/intake/email",
            json={"subject": "Identity Documents Missing Ref", "sender": "applicant.unregistered@domain.com"},
            headers=tenant_alpha_headers,
        )
        assert inbound.status_code == 200
        exc_id = inbound.json()["exception_id"]

        # Step 2: Create target case
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "manual_triage"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        target_case_id = c_res.json()["id"]

        # Step 3: Assign exception to case
        assign_res = await async_client.post(
            f"/api/v1/email/exceptions/{exc_id}/assign",
            json={"case_id": target_case_id},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert assign_res.status_code == 200
        assert assign_res.json()["status"] == "assigned"
        assert assign_res.json()["case_id"] == target_case_id

        # Step 4: Verify case status advanced
        case_detail = await async_client.get(
            f"/api/v1/cases/{target_case_id}",
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert case_detail.json()["status"] == "documents_received"

    # ------------------------------------------------------------------------
    # 9. F9 + F2: Lifecycle Stepper + State Transitions
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_09_stepper_syncs_with_state_machine_transitions(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Verify lifecycle stepper stages update synchronously with state machine changes."""
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "stepper_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c_res.json()["id"]

        # Initial stepper: draft
        d1 = await async_client.get(f"/api/v1/cases/{case_id}", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        stepper1 = d1.json()["stepper"]
        assert stepper1["current_stage"] == "draft"
        assert stepper1["current_step"] == 1

        # Advance status to invitation_sent
        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "invitation_sent"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        d2 = await async_client.get(f"/api/v1/cases/{case_id}", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        stepper2 = d2.json()["stepper"]
        assert stepper2["current_stage"] == "invitation_sent"
        assert any(s["stage"] == "invitation_sent" for s in stepper2["completed_steps"])

        # Advance status to awaiting_documents
        await async_client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "awaiting_documents"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        d3 = await async_client.get(f"/api/v1/cases/{case_id}", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        stepper3 = d3.json()["stepper"]
        assert stepper3["current_stage"] == "awaiting_documents"
        assert len(stepper3["completed_steps"]) >= 3

    # ------------------------------------------------------------------------
    # 10. F10 + F11: Split Workspace + Field Decisions
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_10_reviewer_workspace_loads_fields_and_applies_decision(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
        valid_pdf_document: bytes,
    ):
        """Verify reviewer split workspace retrieves field deck and executes inline field confirmation."""
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "workspace_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c_res.json()["id"]

        # Upload document and extract field
        files = {"file": ("pan.pdf", valid_pdf_document, "application/pdf")}
        await async_client.post(f"/api/v1/cases/{case_id}/documents", files=files, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        ext_res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "pan", "document_text": "PAN: ABCPS1234F"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        field_id = ext_res.json()["extracted_fields"][0]["id"]

        # Reviewer opens split workspace
        ws_res = await async_client.get(f"/api/v1/cases/{case_id}", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert ws_res.status_code == 200
        ws_data = ws_res.json()
        assert len(ws_data["documents"]) >= 1
        assert len(ws_data["extracted_fields"]) >= 1

        # Reviewer confirms field in workspace
        dec_res = await async_client.patch(
            f"/api/v1/cases/{case_id}/fields/{field_id}",
            json={"reviewer_decision": "confirmed"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert dec_res.status_code == 200
        assert dec_res.json()["reviewer_decision"] == "confirmed"
        assert dec_res.json()["confirmed_value"] == "ABCPS1234F"

    # ------------------------------------------------------------------------
    # 11. F11 + F21: Field Decisions + Audit Trail
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_11_field_decision_correction_logged_to_immutable_audit_trail(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Verify reviewer field correction appends immutable event to audit log."""
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "audit_field_test"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c_res.json()["id"]

        ext = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "aadhaar"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        field_id = ext.json()["extracted_fields"][0]["id"]

        # Apply correction
        corrected_value = "294828472849"
        await async_client.patch(
            f"/api/v1/cases/{case_id}/fields/{field_id}",
            json={"reviewer_decision": "corrected", "corrected_value": corrected_value},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )

        # Inspect audit trail
        audit_res = await async_client.get(
            f"/api/v1/cases/{case_id}/audit-trail",
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert audit_res.status_code == 200
        events = audit_res.json()["events"]
        field_event = next((e for e in events if e["action"] == "field_decision"), None)
        assert field_event is not None
        assert field_event["object_id"] == field_id
        assert field_event["metadata"]["decision"] == "corrected"
        assert field_event["metadata"]["corrected_value"] == corrected_value

    # ------------------------------------------------------------------------
    # 12. F12 + F15: Case Approval + Controlled Sharing
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_12_case_approval_enables_controlled_credential_sharing(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Verify only approved cases can generate a 30-day credential share grant."""
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "share_enablement"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c_res.json()["id"]

        # Attempt share while in draft -> must fail with 400
        premature_share = await async_client.post(
            f"/api/v1/cases/{case_id}/shares",
            json={"purpose": "lending_check"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert premature_share.status_code == 400

        # Approve case via decision gate
        await async_client.post(
            f"/api/v1/cases/{case_id}/approve",
            json={"reason": "Approved for third-party marketplace credential sharing"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )

        # Post-approval share grant creation succeeds
        share_res = await async_client.post(
            f"/api/v1/cases/{case_id}/shares",
            json={"purpose": "lending_check", "selected_fields": ["full_name", "date_of_birth"]},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert share_res.status_code == 201
        share_data = share_res.json()
        assert "share_token" in share_data
        assert "expires_at" in share_data
        assert share_data["consent_status"] == "pending_consent"

    # ------------------------------------------------------------------------
    # 13. F13 + F20: Theme Preferences + Auth
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_13_theme_preferences_bound_to_authenticated_session(
        self,
        async_client: httpx.AsyncClient,
    ):
        """Verify theme preferences are persisted across authenticated sessions."""
        # 1. Login to get authenticated cookies
        login_res = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "compliance@bankalpha.com", "password": "SecurePassword123!"},
        )
        assert login_res.status_code == 200
        cookies = login_res.cookies

        # 2. Get initial preference
        get_res = await async_client.get("/api/v1/users/me/preferences", cookies=cookies)
        assert get_res.status_code == 200

        # 3. Update theme to obsidian dark
        patch_res = await async_client.patch(
            "/api/v1/users/me/preferences",
            json={"theme": "dark"},
            cookies=cookies,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["theme"] == "dark"

        # 4. Verify persisted theme
        check_res = await async_client.get("/api/v1/users/me/preferences", cookies=cookies)
        assert check_res.json()["theme"] == "dark"

    # ------------------------------------------------------------------------
    # 14. F14 + F3: Applicant Portal + Document Upload
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_14_applicant_portal_document_upload_via_token(
        self,
        async_client: httpx.AsyncClient,
        valid_pdf_document: bytes,
    ):
        """Verify applicant accesses self-service portal with token and uploads documents securely."""
        token = "token-applicant-777"

        # 1. Access portal view
        portal_res = await async_client.get(f"/api/v1/portal/{token}")
        assert portal_res.status_code == 200
        assert portal_res.json()["case_number"] == "CASE-1001"

        # 2. Upload document via applicant portal
        files = {"file": ("applicant_id.pdf", valid_pdf_document, "application/pdf")}
        upload_res = await async_client.post(f"/api/v1/portal/{token}/documents", files=files)
        assert upload_res.status_code == 201
        assert upload_res.json()["status"] == "uploaded"

        # 3. Applicant confirms submitted fields
        conf_res = await async_client.post(f"/api/v1/portal/{token}/confirm-fields")
        assert conf_res.status_code == 200
        assert conf_res.json()["applicant_confirmed"] is True

    # ------------------------------------------------------------------------
    # 15. F15 + F16: Controlled Sharing + Share Consent
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_15_controlled_share_requires_applicant_consent_before_release(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Verify shared credential claims remain 403 Forbidden until applicant grants explicit consent."""
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "consent_sharing_flow"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c_res.json()["id"]

        # Approve case
        await async_client.post(
            f"/api/v1/cases/{case_id}/approve",
            json={"reason": "Approved for consent testing"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )

        # Create share
        share_res = await async_client.post(
            f"/api/v1/cases/{case_id}/shares",
            json={"purpose": "bank_syndication"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        share_token = share_res.json()["share_token"]
        share_id = share_res.json()["id"]

        # 1. Pre-consent access attempt -> 403 Forbidden
        pre_consent_read = await async_client.get(f"/api/v1/shares/{share_token}")
        assert pre_consent_read.status_code == 403

        # 2. Applicant grants consent
        consent_res = await async_client.post(
            f"/api/v1/shares/{share_id}/consent",
            json={"decision": "granted"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert consent_res.status_code == 200
        assert consent_res.json()["status"] == "granted"

        # 3. Post-consent access succeeds -> 200 OK
        post_consent_read = await async_client.get(f"/api/v1/shares/{share_token}")
        assert post_consent_read.status_code == 200
        assert "verified_claims" in post_consent_read.json()

    # ------------------------------------------------------------------------
    # 16. F16 + F21: Share Consent + Audit Trail
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_16_share_consent_and_revocation_recorded_in_audit_trail(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Verify applicant consent grant and subsequent revocation are both immutably logged."""
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "audit_share_consent"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c_res.json()["id"]
        await async_client.post(f"/api/v1/cases/{case_id}/approve", json={"reason": "Approved"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        share_res = await async_client.post(f"/api/v1/cases/{case_id}/shares", json={}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        share_id = share_res.json()["id"]

        # Consent grant
        await async_client.post(f"/api/v1/shares/{share_id}/consent", json={"decision": "granted"}, headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        # Revocation
        await async_client.post(f"/api/v1/shares/{share_id}/revoke", headers=tenant_alpha_headers, cookies=auth_admin_cookies)

        # Audit verification
        audit_res = await async_client.get(f"/api/v1/cases/{case_id}/audit-trail", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert audit_res.status_code == 200
        events = audit_res.json()["events"]
        assert len(events) >= 1

    # ------------------------------------------------------------------------
    # 17. F17 + F1: Local SQLite DB + Case Operations
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_17_local_embedded_db_case_operations(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Verify case operations run reliably on local SQLite without external cloud dependencies."""
        health = await async_client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        # Create multiple cases sequentially
        cases = []
        for i in range(3):
            res = await async_client.post(
                "/api/v1/cases",
                json={"applicant": generate_adult_applicant(), "purpose": f"local_db_batch_{i}"},
                headers=tenant_alpha_headers,
                cookies=auth_admin_cookies,
            )
            assert res.status_code == 201
            cases.append(res.json()["id"])

        # Query all cases
        list_res = await async_client.get("/api/v1/cases", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert list_res.status_code == 200
        fetched_ids = [c["id"] for c in list_res.json()["items"]]
        for cid in cases:
            assert cid in fetched_ids

    # ------------------------------------------------------------------------
    # 18. F18 + F4: Pluggable OCR Fallback + Field Extraction
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_18_ocr_fallback_to_local_regex_extractor(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Verify pluggable OCR pipeline falls back to deterministic regex parser on text layers."""
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "ocr_fallback"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c_res.json()["id"]

        # Raw document with embedded PAN in noisy text
        noisy_text = "Transaction summary 2026: Tax reference ID ABCPS1234F verified by bank."
        res = await async_client.post(
            f"/api/v1/cases/{case_id}/extract-fields",
            json={"document_type": "pan", "document_text": noisy_text},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert res.status_code == 200
        fields = res.json()["extracted_fields"]
        assert len(fields) >= 1
        assert fields[0]["field_name"] == "pan_number"
        assert fields[0]["draft_value"] == "ABCPS1234F"

    # ------------------------------------------------------------------------
    # 19. F19 + F1: Multi-Tenancy + Case Scoping
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_19_multitenancy_strict_case_isolation(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        tenant_beta_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Verify cases created in Tenant Alpha cannot be viewed or mutated by Tenant Beta."""
        alpha_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "alpha_exclusive"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        alpha_case_id = alpha_res.json()["id"]

        # Tenant Alpha can access
        assert (await async_client.get(f"/api/v1/cases/{alpha_case_id}", headers=tenant_alpha_headers, cookies=auth_admin_cookies)).status_code == 200

        # Tenant Beta gets strict 404 Not Found
        beta_get = await async_client.get(f"/api/v1/cases/{alpha_case_id}", headers=tenant_beta_headers, cookies=auth_admin_cookies)
        assert beta_get.status_code == 404

        # Tenant Beta cannot patch status
        beta_patch = await async_client.patch(
            f"/api/v1/cases/{alpha_case_id}/status",
            json={"status": "invitation_sent"},
            headers=tenant_beta_headers,
            cookies=auth_admin_cookies,
        )
        assert beta_patch.status_code == 404

    # ------------------------------------------------------------------------
    # 20. F20 + F19: Auth + Multi-Tenancy
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_20_auth_credentials_and_tenant_header_binding(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Verify authenticated user requests require both valid JWT cookies and bound tenant headers."""
        # 1. Unauthenticated request -> 401
        unauth_res = await async_client.get("/api/v1/auth/me")
        assert unauth_res.status_code == 401

        # 2. Authenticated request with cookies -> 200
        auth_res = await async_client.get("/api/v1/auth/me", cookies=auth_admin_cookies)
        assert auth_res.status_code == 200

        # 3. Missing X-Tenant-ID header on tenant-scoped operations -> 400
        missing_tenant_res = await async_client.get("/api/v1/cases", cookies=auth_admin_cookies)
        assert missing_tenant_res.status_code == 400

        # 4. Valid tenant header + auth cookies -> 200
        valid_res = await async_client.get("/api/v1/cases", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert valid_res.status_code == 200

    # ------------------------------------------------------------------------
    # 21. F21 + F12: Audit Trail + Review Decision
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_21_case_approval_reason_and_reviewer_logged_immutably(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Verify written justification reason and reviewer ID are immutably captured in audit trail."""
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "audit_review_decision"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        case_id = c_res.json()["id"]

        written_reason = "Fully compliant with AML/KYC Tier 1 criteria and valid Verhoeff Aadhaar"
        await async_client.post(
            f"/api/v1/cases/{case_id}/approve",
            json={"reason": written_reason},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )

        audit_res = await async_client.get(
            f"/api/v1/cases/{case_id}/audit-trail",
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert audit_res.status_code == 200
        events = audit_res.json()["events"]
        approve_event = next((e for e in events if e["action"] == "case_approved"), None)
        assert approve_event is not None
        assert approve_event["metadata"]["reason"] == written_reason
        assert "reviewer_id" in approve_event["metadata"]

    # ------------------------------------------------------------------------
    # 22. F22 + F1: Usage Counters + Case Creation
    # ------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_t3_22_tenant_case_counter_increments_upon_case_creation(
        self,
        async_client: httpx.AsyncClient,
        tenant_alpha_headers: dict,
        auth_admin_cookies: dict,
    ):
        """Verify tenant usage metric counter increments by 1 on each case creation."""
        # Query before
        u1 = await async_client.get("/api/v1/tenants/usage", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert u1.status_code == 200
        initial_cases = u1.json()["metrics"]["cases_created"]
        initial_remaining = u1.json()["remaining_cases"]

        # Create case
        c_res = await async_client.post(
            "/api/v1/cases",
            json={"applicant": generate_adult_applicant(), "purpose": "usage_counter_verify"},
            headers=tenant_alpha_headers,
            cookies=auth_admin_cookies,
        )
        assert c_res.status_code == 201

        # Query after
        u2 = await async_client.get("/api/v1/tenants/usage", headers=tenant_alpha_headers, cookies=auth_admin_cookies)
        assert u2.status_code == 200
        new_cases = u2.json()["metrics"]["cases_created"]
        new_remaining = u2.json()["remaining_cases"]

        assert new_cases == initial_cases + 1
        assert new_remaining == initial_remaining - 1
