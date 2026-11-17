"""KYC Case 11-Stage Workflow State Machine & Reviewer Decision Gates."""
from enum import Enum
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent
from app.models.case import KycCase
from app.models.user import User


class CaseStatus(str, Enum):
    DRAFT = "draft"
    INVITATION_SENT = "invitation_sent"
    AWAITING_DOCUMENTS = "awaiting_documents"
    DOCUMENTS_RECEIVED = "documents_received"
    OCR_PROCESSING = "ocr_processing"
    NEEDS_APPLICANT_CORRECTION = "needs_applicant_correction"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CLOSED = "closed"


VALID_TRANSITIONS: Dict[CaseStatus, List[CaseStatus]] = {
    CaseStatus.DRAFT: [
        CaseStatus.INVITATION_SENT,
        CaseStatus.AWAITING_DOCUMENTS,
        CaseStatus.DOCUMENTS_RECEIVED,  # Added for direct email intake
        CaseStatus.CLOSED,
    ],
    CaseStatus.INVITATION_SENT: [
        CaseStatus.AWAITING_DOCUMENTS,
        CaseStatus.DOCUMENTS_RECEIVED,  # Added for applicant reply intake
        CaseStatus.EXPIRED,
        CaseStatus.CLOSED,
    ],
    CaseStatus.AWAITING_DOCUMENTS: [
        CaseStatus.DOCUMENTS_RECEIVED,
        CaseStatus.EXPIRED,
        CaseStatus.CLOSED,
    ],
    CaseStatus.DOCUMENTS_RECEIVED: [
        CaseStatus.OCR_PROCESSING,
        CaseStatus.IN_REVIEW,
        CaseStatus.CLOSED,
    ],
    CaseStatus.OCR_PROCESSING: [
        CaseStatus.IN_REVIEW,
        CaseStatus.NEEDS_APPLICANT_CORRECTION,
        CaseStatus.CLOSED,
    ],
    CaseStatus.NEEDS_APPLICANT_CORRECTION: [
        CaseStatus.DOCUMENTS_RECEIVED,
        CaseStatus.CLOSED,
    ],
    CaseStatus.IN_REVIEW: [
        CaseStatus.NEEDS_APPLICANT_CORRECTION,
        CaseStatus.APPROVED,
        CaseStatus.REJECTED,
        CaseStatus.CLOSED,
    ],
    CaseStatus.APPROVED: [CaseStatus.CLOSED],
    CaseStatus.REJECTED: [CaseStatus.CLOSED],
    CaseStatus.EXPIRED: [CaseStatus.CLOSED],
    CaseStatus.CLOSED: [],
}

TERMINAL_STATUSES = {CaseStatus.APPROVED, CaseStatus.REJECTED, CaseStatus.EXPIRED, CaseStatus.CLOSED}


async def transition_case(
    case: KycCase,
    new_status: CaseStatus,
    user: Optional[User] = None,
    reason: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> KycCase:
    """Validates state transitions and enforces reviewer decision gates."""
    curr_status = CaseStatus(case.status)

    if curr_status in TERMINAL_STATUSES and new_status != CaseStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition out of terminal state '{curr_status.value}'",
        )

    allowed = VALID_TRANSITIONS.get(curr_status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Illegal state jump from '{curr_status.value}' to '{new_status.value}'",
        )

    # Decision gate for APPROVED / REJECTED
    if new_status in (CaseStatus.APPROVED, CaseStatus.REJECTED):
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required for case approval or rejection",
            )
        is_admin_or_reviewer = (
            user.is_platform_admin
            or getattr(user, "active_role", None) in ("reviewer", "tenant_admin", "platform_admin")
        )
        if not is_admin_or_reviewer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only reviewers and tenant admins may approve or reject cases",
            )
        if not reason or not reason.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Review justification reason is required for approval or rejection",
            )

        case.review_decision = new_status.value
        case.review_reason = reason.strip()
        case.reviewer_id = user.id

    case.status = new_status.value

    if db:
        evt = AuditEvent(
            tenant_id=case.tenant_id,
            actor_id=user.id if user else None,
            actor_role=getattr(user, "active_role", "system") if user else "system",
            action="case_status_transition",
            resource_type="case",
            resource_id=case.id,
            metadata_={
                "from_status": curr_status.value,
                "to_status": new_status.value,
                "reason": reason,
            },
        )
        db.add(evt)

    return case
