"""Verification Endpoints: OCR Extraction, Rule Validation, Biometrics, and Reviewer Decisions."""
from datetime import datetime
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_scoped_or_404
from app.core.dependencies import get_current_user, get_tenant_context, require_reviewer
from app.models.audit import AuditEvent
from app.models.case import KycCase
from app.models.document import CaseDocument
from app.models.field import ExtractedField
from app.models.user import User
from app.schemas.verification import (
    DocumentExtractionRequest,
    DocumentExtractionResponse,
    ExtractedFieldResponse,
    FieldDecisionRequest,
    KYCValidationRequest,
    KYCValidationResponse,
    SelfieMatchResponse,
    ValidationIssueResponse,
)
from app.services.face_matching.matcher import face_matcher
from app.services.ocr.tier_manager import ocr_engine
from app.services.storage.local import storage_service
from app.services.validation.engine import validation_engine

router = APIRouter()


@router.post("/cases/{case_id}/extract-fields", response_model=DocumentExtractionResponse)
async def extract_fields(
    case_id: str,
    payload: DocumentExtractionRequest,
    current_user: User = Depends(require_reviewer),
    tenant_id: uuid.UUID = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Executes multi-tier OCR field extraction from document text or stored document bytes."""
    try:
        case_uuid = uuid.UUID(str(case_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    case = await get_scoped_or_404(db, KycCase, case_uuid, tenant_id=tenant_id)

    file_bytes = None
    target_doc_id = None
    if payload.document_id:
        try:
            target_doc_id = uuid.UUID(str(payload.document_id))
        except (ValueError, AttributeError):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # If document_id is provided, read bytes from local disk
    if target_doc_id:
        doc = await get_scoped_or_404(db, CaseDocument, target_doc_id, tenant_id=tenant_id)
        if doc.case_id != case_uuid:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document does not belong to case")
        file_bytes = storage_service.read_file(doc.storage_key)
    elif not payload.document_text:
        # Check if case has any documents uploaded
        stmt = (
            select(CaseDocument)
            .where(CaseDocument.case_id == case_uuid, CaseDocument.tenant_id == tenant_id)
            .order_by(CaseDocument.uploaded_at.desc())
        )
        recent_doc = (await db.execute(stmt)).scalars().first()
        if recent_doc:
            target_doc_id = recent_doc.id
            file_bytes = storage_service.read_file(recent_doc.storage_key)

    ocr_result = await ocr_engine.extract_fields(
        document_type=payload.document_type,
        file_bytes=file_bytes,
        document_text=payload.document_text,
    )

    persisted_fields: List[ExtractedFieldResponse] = []
    for f in ocr_result.extracted_fields:
        field_id = uuid.uuid4()
        field_model = ExtractedField(
            id=field_id,
            tenant_id=tenant_id,
            document_id=target_doc_id or uuid.uuid4(),  # placeholder if unassociated text
            field_name=f.field_name,
            draft_value=f.draft_value,
            confirmed_value=None,
            source_page=f.source_page,
            confidence=f.confidence,
            applicant_confirmed=False,
            reviewer_decision="pending",
            correction_history=[],
        )
        if target_doc_id:
            db.add(field_model)

        persisted_fields.append(
            ExtractedFieldResponse(
                id=field_id,
                case_id=case_uuid,
                tenant_id=tenant_id,
                document_id=target_doc_id,
                field_name=f.field_name,
                draft_value=f.draft_value,
                confirmed_value=None,
                source_page=f.source_page,
                confidence=f.confidence,
                applicant_confirmed=False,
                reviewer_decision="pending",
                correction_history=[],
            )
        )

    if target_doc_id:
        await db.flush()

    return DocumentExtractionResponse(
        count=len(persisted_fields),
        fallback_applied=ocr_result.fallback_applied,
        extracted_fields=persisted_fields,
    )


@router.post("/cases/{case_id}/validate", response_model=KYCValidationResponse)
async def validate_case(
    case_id: str,
    payload: KYCValidationRequest,
    current_user: User = Depends(require_reviewer),
    tenant_id: uuid.UUID = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Executes rule-based validation engine across identity fields and cross-validates demographics."""
    try:
        case_uuid = uuid.UUID(str(case_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    case = await get_scoped_or_404(db, KycCase, case_uuid, tenant_id=tenant_id)

    app_type = case.case_type if case.case_type else "person"
    val_res = validation_engine.validate(
        aadhaar_number=payload.aadhaar_number,
        pan_number=payload.pan_number,
        passport_mrz=payload.passport_mrz,
        dl_number=payload.dl_number,
        date_of_birth=payload.date_of_birth,
        expiry_date=payload.expiry_date,
        applicant_name=payload.applicant_name,
        extracted_name=payload.extracted_name,
        applicant_type=app_type,
    )

    issues_response = [
        ValidationIssueResponse(
            code=i.code,
            field_name=i.field_name,
            severity=i.severity,
            message=i.message,
        )
        for i in val_res.issues
    ]

    # Save to case model
    case.validation_issues = [i.model_dump() for i in issues_response]
    await db.flush()

    return KYCValidationResponse(
        is_valid=val_res.is_valid,
        issues=issues_response,
        error_count=val_res.error_count,
        warning_count=val_res.warning_count,
        issue_count=len(issues_response),
        recommendation=val_res.recommendation,
    )


@router.post("/cases/{case_id}/selfie-match", response_model=SelfieMatchResponse)
async def selfie_match(
    case_id: str,
    selfie: UploadFile = File(...),
    id_photo: Optional[UploadFile] = File(None),
    threshold: float = Form(0.75),
    current_user: User = Depends(require_reviewer),
    tenant_id: uuid.UUID = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Executes biometric facial comparison between applicant selfie and ID document photograph."""
    try:
        case_uuid = uuid.UUID(str(case_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    case = await get_scoped_or_404(db, KycCase, case_uuid, tenant_id=tenant_id)

    selfie_bytes = await selfie.read()
    id_bytes = None

    if id_photo:
        id_bytes = await id_photo.read()
    else:
        # Search for identity document on the case
        stmt = (
            select(CaseDocument)
            .where(
                CaseDocument.case_id == case_uuid,
                CaseDocument.tenant_id == tenant_id,
                CaseDocument.document_type.in_(["identity_card", "aadhaar", "passport", "pan", "driving_licence", "id_card"]),
            )
            .order_by(CaseDocument.uploaded_at.desc())
        )
        doc = (await db.execute(stmt)).scalars().first()
        if doc:
            id_bytes = storage_service.read_file(doc.storage_key)

    match_res = face_matcher.compare_faces(
        selfie_bytes=selfie_bytes,
        id_doc_bytes=id_bytes,
        threshold=threshold,
    )

    response_payload = {
        "case_id": str(case_uuid),
        "is_match": match_res.is_match,
        "confidence": match_res.confidence,
        "threshold": threshold,
        "method": match_res.method,
        "details": match_res.details,
    }

    case.selfie_match = response_payload

    audit_evt = AuditEvent(
        tenant_id=tenant_id,
        actor_id=current_user.id,
        actor_role=current_user.active_role or "reviewer",
        action="selfie_match",
        resource_type="case",
        resource_id=case_uuid,
        metadata_=response_payload,
    )
    db.add(audit_evt)
    await db.flush()

    return SelfieMatchResponse(**response_payload)


@router.patch("/cases/{case_id}/fields/{field_id}", response_model=ExtractedFieldResponse)
async def update_field_decision(
    case_id: str,
    field_id: str,
    payload: FieldDecisionRequest,
    current_user: User = Depends(require_reviewer),
    tenant_id: uuid.UUID = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Reviewer controls to accept, correct, or reject an extracted field."""
    try:
        case_uuid = uuid.UUID(str(case_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    case = await get_scoped_or_404(db, KycCase, case_uuid, tenant_id=tenant_id)

    if case.status in ("approved", "closed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot modify fields of a case in '{case.status}' status",
        )

    try:
        field_uuid = uuid.UUID(str(field_id))
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ExtractedField '{field_id}' not found",
        )

    field = await get_scoped_or_404(db, ExtractedField, field_uuid, tenant_id=tenant_id)

    decision = payload.reviewer_decision.lower()
    if decision not in ("confirmed", "corrected", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid reviewer decision: '{decision}'",
        )

    correction_entry = None
    if decision == "confirmed":
        field.confirmed_value = field.draft_value
    elif decision == "corrected":
        if payload.corrected_value is None or not str(payload.corrected_value).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Corrected value cannot be empty when decision is 'corrected'",
            )
        old_val = field.confirmed_value if field.confirmed_value is not None else field.draft_value
        new_val = str(payload.corrected_value).strip()
        field.confirmed_value = new_val

        history = list(field.correction_history or [])
        correction_entry = {
            "from_value": old_val,
            "to_value": new_val,
            "timestamp": datetime.utcnow().isoformat(),
            "reviewer_id": str(current_user.id),
        }
        history.append(correction_entry)
        field.correction_history = history
    elif decision == "rejected":
        field.confirmed_value = None

    field.reviewer_decision = decision
    if payload.reviewer_notes:
        field.reviewer_notes = payload.reviewer_notes

    audit_evt = AuditEvent(
        tenant_id=tenant_id,
        actor_id=current_user.id,
        actor_role=current_user.active_role or "reviewer",
        action="field_decision",
        resource_type="extracted_field",
        resource_id=field.id,
        metadata_={
            "case_id": str(case_uuid),
            "decision": decision,
            "correction": correction_entry,
        },
    )
    db.add(audit_evt)
    await db.flush()

    return ExtractedFieldResponse(
        id=field.id,
        case_id=case_uuid,
        tenant_id=field.tenant_id,
        document_id=field.document_id,
        field_name=field.field_name,
        draft_value=field.draft_value,
        confirmed_value=field.confirmed_value,
        source_page=field.source_page,
        confidence=field.confidence,
        applicant_confirmed=field.applicant_confirmed,
        reviewer_decision=field.reviewer_decision,
        reviewer_notes=field.reviewer_notes,
        correction_history=field.correction_history,
    )
