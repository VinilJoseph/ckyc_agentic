"""KYC Cases Router: CRUD, Listing, Transitions, Approve & Reject Endpoints, and Case Hydration."""
import random
from typing import List, Optional, Union
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.context import get_current_tenant_id
from app.core.database import get_db, get_scoped_or_404
from app.core.dependencies import get_tenant_context, require_reviewer
from app.core.state_machine import CaseStatus, transition_case
from app.models.applicant import Applicant, BusinessRepresentative
from app.models.case import KycCase
from app.models.document import CaseDocument
from app.models.field import ExtractedField
from app.models.user import User
from app.schemas.case import (
    ApplicantDetailResponse,
    CaseCreate,
    CaseDecisionRequest,
    CaseDetailResponse,
    CaseListItem,
    CaseResponse,
    CaseTransitionRequest,
)
from app.schemas.common import PaginatedResponse
from app.schemas.document import CaseDocumentResponse
from app.schemas.verification import ExtractedFieldResponse, SelfieMatchResponse, ValidationIssueResponse

router = APIRouter()


async def generate_unique_case_number(db: AsyncSession) -> str:
    """Generate collision-resistant case number (CASE-XXXX)."""
    for _ in range(10):
        candidate = f"CASE-{random.randint(1000, 9999)}"
        stmt = (
            select(KycCase.id)
            .where(KycCase.case_number == candidate)
            .execution_options(bypass_tenant_isolation=True)
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if not existing:
            return candidate
    return f"CASE-{uuid.uuid4().hex[:6].upper()}"


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    payload: CaseCreate,
    current_user: User = Depends(require_reviewer),
    tenant_id: uuid.UUID = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    app_data = payload.applicant
    applicant = Applicant(
        tenant_id=tenant_id,
        applicant_type=app_data.applicant_type,
        email=app_data.email,
        phone=app_data.phone,
        first_name=app_data.first_name,
        last_name=app_data.last_name,
        date_of_birth=app_data.date_of_birth,
        nationality=app_data.nationality,
        business_name=app_data.business_name,
        registration_number=app_data.registration_number,
        incorporation_date=app_data.incorporation_date,
    )
    db.add(applicant)
    await db.flush()

    if app_data.representatives:
        for rep in app_data.representatives:
            r = BusinessRepresentative(
                tenant_id=tenant_id,
                business_id=applicant.id,
                full_name=rep.full_name,
                role_title=rep.role_title,
                email=rep.email,
            )
            db.add(r)
        await db.flush()

    case_number = await generate_unique_case_number(db)
    case = KycCase(
        tenant_id=tenant_id,
        applicant_id=applicant.id,
        case_number=case_number,
        purpose=payload.purpose,
        case_type=payload.case_type,
        status=CaseStatus.DRAFT.value,
    )
    db.add(case)
    await db.flush()
    return case


@router.get("", response_model=PaginatedResponse[CaseListItem])
async def list_cases(
    status_filter: Optional[str] = Query(None, alias="status"),
    case_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_reviewer),
    tenant_id: uuid.UUID = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(KycCase)
        .options(selectinload(KycCase.applicant))
        .where(KycCase.tenant_id == tenant_id)
    )
    if status_filter:
        stmt = stmt.where(KycCase.status == status_filter)
    if case_type:
        stmt = stmt.where(KycCase.case_type == case_type)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(KycCase.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    cases = (await db.execute(stmt)).scalars().all()

    items = []
    for c in cases:
        app_name = (
            f"{c.applicant.first_name or ''} {c.applicant.last_name or ''}".strip()
            if c.applicant.applicant_type == "person"
            else (c.applicant.business_name or "Unknown")
        )
        items.append(
            CaseListItem(
                id=c.id,
                tenant_id=c.tenant_id,
                case_number=c.case_number,
                purpose=c.purpose,
                case_type=c.case_type,
                status=c.status,
                applicant_name=app_name or "Unnamed Applicant",
                applicant_type=c.applicant.applicant_type,
                created_at=c.created_at,
                expires_at=c.expires_at,
            )
        )

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
    )


@router.get("/{id}", response_model=CaseDetailResponse)
async def get_case(
    id: str,
    current_user: User = Depends(require_reviewer),
    tenant_id: uuid.UUID = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Fetches case details with hydrated documents, extracted fields, validation issues, and selfie match."""
    try:
        case_uuid = uuid.UUID(str(id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    case = await get_scoped_or_404(db, KycCase, case_uuid, tenant_id=tenant_id)
    stmt = (
        select(Applicant)
        .options(selectinload(Applicant.representatives))
        .where(Applicant.id == case.applicant_id, Applicant.tenant_id == tenant_id)
    )
    applicant = (await db.execute(stmt)).scalar_one()

    reps = [
        {"id": str(r.id), "full_name": r.full_name, "role_title": r.role_title, "email": r.email}
        for r in applicant.representatives
    ]

    app_detail = ApplicantDetailResponse(
        id=applicant.id,
        applicant_type=applicant.applicant_type,
        email=applicant.email,
        phone=applicant.phone,
        first_name=applicant.first_name,
        last_name=applicant.last_name,
        date_of_birth=applicant.date_of_birth,
        nationality=applicant.nationality,
        business_name=applicant.business_name,
        registration_number=applicant.registration_number,
        incorporation_date=applicant.incorporation_date,
        representatives=reps,
    )

    # 1. Fetch documents
    doc_stmt = (
        select(CaseDocument)
        .where(CaseDocument.case_id == case.id, CaseDocument.tenant_id == tenant_id)
        .order_by(CaseDocument.uploaded_at.desc())
    )
    docs_records = (await db.execute(doc_stmt)).scalars().all()
    doc_count = len(docs_records)

    docs_list = [
        CaseDocumentResponse(
            id=d.id,
            case_id=d.case_id,
            tenant_id=d.tenant_id,
            document_type=d.document_type,
            storage_key=d.storage_key,
            original_filename=d.original_filename,
            file_hash=d.file_hash,
            mime_type=d.mime_type,
            file_size=d.file_size,
            source=d.source,
            review_status=d.review_status,
            preview_url=f"/api/v1/cases/{case.id}/documents/{d.id}/preview",
            uploaded_at=d.uploaded_at,
            reviewed_at=d.reviewed_at,
        )
        for d in docs_records
    ]

    # 2. Fetch extracted fields across case documents
    fields_list = []
    if docs_records:
        doc_ids = [d.id for d in docs_records]
        fld_stmt = (
            select(ExtractedField)
            .where(ExtractedField.document_id.in_(doc_ids), ExtractedField.tenant_id == tenant_id)
            .order_by(ExtractedField.created_at.asc())
        )
        field_records = (await db.execute(fld_stmt)).scalars().all()
        fields_list = [
            ExtractedFieldResponse(
                id=f.id,
                case_id=case.id,
                tenant_id=f.tenant_id,
                document_id=f.document_id,
                field_name=f.field_name,
                draft_value=f.draft_value,
                confirmed_value=f.confirmed_value,
                source_page=f.source_page,
                confidence=f.confidence,
                applicant_confirmed=f.applicant_confirmed,
                reviewer_decision=f.reviewer_decision,
                reviewer_notes=f.reviewer_notes,
                correction_history=f.correction_history or [],
            )
            for f in field_records
        ]

    # 3. Validation issues
    val_issues = []
    if case.validation_issues and isinstance(case.validation_issues, list):
        for iss in case.validation_issues:
            val_issues.append(
                ValidationIssueResponse(
                    code=iss.get("code", "UNKNOWN_ISSUE"),
                    field_name=iss.get("field_name", "unknown"),
                    severity=iss.get("severity", "ERROR"),
                    message=iss.get("message", ""),
                )
            )

    # 4. Selfie match
    selfie_match_resp = None
    if case.selfie_match and isinstance(case.selfie_match, dict):
        selfie_match_resp = SelfieMatchResponse(**case.selfie_match)

    return CaseDetailResponse(
        id=case.id,
        tenant_id=case.tenant_id,
        applicant_id=case.applicant_id,
        case_number=case.case_number,
        purpose=case.purpose,
        case_type=case.case_type,
        status=case.status,
        reviewer_id=case.reviewer_id,
        review_decision=case.review_decision,
        review_reason=case.review_reason,
        reason=case.review_reason,
        reviewed_at=case.reviewed_at,
        created_at=case.created_at,
        updated_at=case.updated_at,
        expires_at=case.expires_at,
        applicant=app_detail,
        document_count=doc_count,
        documents=docs_list,
        extracted_fields=fields_list,
        validation_issues=val_issues,
        selfie_match=selfie_match_resp,
        stepper={
            "current_stage": case.status,
            "current_step": 4 if case.status == "documents_received" else 1,
            "completed_steps": [],
        },
    )


@router.patch("/{id}/status", response_model=CaseResponse)
async def transition_case_status(
    id: str,
    payload: CaseTransitionRequest,
    current_user: User = Depends(require_reviewer),
    tenant_id: uuid.UUID = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        case_uuid = uuid.UUID(str(id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    case = await get_scoped_or_404(db, KycCase, case_uuid, tenant_id=tenant_id)
    try:
        target_status = CaseStatus(payload.status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid target status: '{payload.status}'",
        )

    updated_case = await transition_case(
        case=case,
        new_status=target_status,
        user=current_user,
        reason=payload.reason,
        db=db,
    )
    await db.flush()
    return updated_case


@router.post("/{id}/approve", response_model=CaseResponse)
async def approve_case(
    id: str,
    payload: CaseDecisionRequest,
    current_user: User = Depends(require_reviewer),
    tenant_id: uuid.UUID = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Dedicated final review approval endpoint (PROJECT.md:81)."""
    try:
        case_uuid = uuid.UUID(str(id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    case = await get_scoped_or_404(db, KycCase, case_uuid, tenant_id=tenant_id)
    decision_reason = payload.review_reason or payload.reason
    updated_case = await transition_case(
        case=case,
        new_status=CaseStatus.APPROVED,
        user=current_user,
        reason=decision_reason,
        db=db,
    )
    await db.flush()
    return updated_case


@router.post("/{id}/reject", response_model=CaseResponse)
async def reject_case(
    id: str,
    payload: CaseDecisionRequest,
    current_user: User = Depends(require_reviewer),
    tenant_id: uuid.UUID = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Dedicated final review rejection endpoint (PROJECT.md:81)."""
    try:
        case_uuid = uuid.UUID(str(id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    case = await get_scoped_or_404(db, KycCase, case_uuid, tenant_id=tenant_id)
    decision_reason = payload.review_reason or payload.reason
    updated_case = await transition_case(
        case=case,
        new_status=CaseStatus.REJECTED,
        user=current_user,
        reason=decision_reason,
        db=db,
    )
    await db.flush()
    return updated_case
