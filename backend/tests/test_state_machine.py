"""Unit tests for KYC Case 11-stage state machine and decision gates."""
import uuid
import pytest
from fastapi import HTTPException

from app.core.state_machine import CaseStatus, VALID_TRANSITIONS, TERMINAL_STATUSES, transition_case
from app.models.case import KycCase
from app.models.user import User


def make_dummy_case(initial_status: CaseStatus = CaseStatus.DRAFT) -> KycCase:
    return KycCase(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        applicant_id=uuid.uuid4(),
        case_number="CASE-9999",
        purpose="Test Purpose",
        case_type="individual",
        status=initial_status.value,
    )


def make_user(role: str = "reviewer", is_platform_admin: bool = False) -> User:
    u = User(
        id=uuid.uuid4(),
        email=f"user_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Jane Reviewer",
        hashed_password="hashed_pwd",
        is_platform_admin=is_platform_admin,
    )
    # Set dynamic active_role attribute used by state machine
    u.active_role = role
    return u


def test_case_status_enum_coverage():
    """Verify all 11 defined workflow states exist."""
    expected = {
        "draft", "invitation_sent", "awaiting_documents", "documents_received",
        "ocr_processing", "needs_applicant_correction", "in_review",
        "approved", "rejected", "expired", "closed"
    }
    actual = {s.value for s in CaseStatus}
    assert actual == expected


@pytest.mark.asyncio
async def test_valid_forward_transitions():
    """Verify permitted transitions succeed."""
    case = make_dummy_case(CaseStatus.DRAFT)
    
    # DRAFT -> AWAITING_DOCUMENTS
    await transition_case(case, CaseStatus.AWAITING_DOCUMENTS)
    assert case.status == CaseStatus.AWAITING_DOCUMENTS.value

    # AWAITING_DOCUMENTS -> DOCUMENTS_RECEIVED
    await transition_case(case, CaseStatus.DOCUMENTS_RECEIVED)
    assert case.status == CaseStatus.DOCUMENTS_RECEIVED.value

    # DOCUMENTS_RECEIVED -> OCR_PROCESSING
    await transition_case(case, CaseStatus.OCR_PROCESSING)
    assert case.status == CaseStatus.OCR_PROCESSING.value

    # OCR_PROCESSING -> IN_REVIEW
    await transition_case(case, CaseStatus.IN_REVIEW)
    assert case.status == CaseStatus.IN_REVIEW.value


@pytest.mark.asyncio
async def test_illegal_state_jump_raises_400():
    """Verify illegal transitions trigger HTTP 400."""
    case = make_dummy_case(CaseStatus.DRAFT)
    
    with pytest.raises(HTTPException) as exc_info:
        await transition_case(case, CaseStatus.APPROVED)
    assert exc_info.value.status_code == 400
    assert "Illegal state jump" in exc_info.value.detail


@pytest.mark.asyncio
async def test_terminal_state_exit_raises_400():
    """Verify cannot transition out of terminal state except to closed."""
    case = make_dummy_case(CaseStatus.APPROVED)
    
    with pytest.raises(HTTPException) as exc_info:
        await transition_case(case, CaseStatus.IN_REVIEW)
    assert exc_info.value.status_code == 400
    assert "terminal state" in exc_info.value.detail

    # Terminal state -> closed is allowed
    await transition_case(case, CaseStatus.CLOSED)
    assert case.status == CaseStatus.CLOSED.value


@pytest.mark.asyncio
async def test_approval_decision_gate():
    """Verify approval requires authentication, reviewer role, and justification."""
    case = make_dummy_case(CaseStatus.IN_REVIEW)
    
    # 1. No user -> 401
    with pytest.raises(HTTPException) as exc_info:
        await transition_case(case, CaseStatus.APPROVED, user=None, reason="Looks good")
    assert exc_info.value.status_code == 401

    # 2. Unauthorized role -> 403
    unauth_user = make_user(role="viewer")
    with pytest.raises(HTTPException) as exc_info:
        await transition_case(case, CaseStatus.APPROVED, user=unauth_user, reason="Looks good")
    assert exc_info.value.status_code == 403

    # 3. Missing reason -> 422
    reviewer_user = make_user(role="reviewer")
    with pytest.raises(HTTPException) as exc_info:
        await transition_case(case, CaseStatus.APPROVED, user=reviewer_user, reason="")
    assert exc_info.value.status_code == 422

    # 4. Valid reviewer with reason -> Approved successfully
    await transition_case(
        case, CaseStatus.APPROVED, user=reviewer_user, reason="All documents verified against UIDAI"
    )
    assert case.status == CaseStatus.APPROVED.value
    assert case.review_decision == CaseStatus.APPROVED.value
    assert case.review_reason == "All documents verified against UIDAI"
    assert case.reviewer_id == reviewer_user.id
