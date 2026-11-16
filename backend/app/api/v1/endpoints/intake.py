"""FastAPI Endpoints for Email Intake & Email Exception Queue (Milestone 3).

Endpoints:
- POST /api/v1/intake/email: JSON webhook intake simulator
- POST /api/v1/intake/eml: Raw RFC 822 .eml multipart upload
- GET /api/v1/email/exceptions: List unmatched email exceptions with pagination
- POST /api/v1/email/exceptions/{id}/assign: Manually assign unmatched exception to target case
- POST /api/v1/email/exceptions/{id}/dismiss: Dismiss junk/spam email exception
"""
import base64
from datetime import datetime, timezone
import hashlib
import re
from typing import List, Optional, Union
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.email import MailIngestionRecord
from app.models.user import User
from app.schemas.email import (
    EmailExceptionAssignRequest,
    EmailExceptionAssignResponse,
    EmailExceptionDismissResponse,
    EmailExceptionItem,
    EmailExceptionListResponse,
    EmailIntakeResponse,
    EmailWebhookRequest,
    MailIngestionRecordRead,
)
from app.services.email.parser import (
    CASE_NUMBER_REGEX,
    ParsedAttachmentDTO,
    ParsedEmailDTO,
    parse_rfc822_email,
)
from app.services.email.service import email_intake_service

router = APIRouter()


async def get_optional_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Extracts authenticated user if cookies/headers present, without blocking unauthenticated intake."""
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None


def resolve_tenant_id(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    user: Optional[User] = None,
) -> uuid.UUID:
    """Deterministically resolves tenant UUID from header or active user session."""
    raw_tid = x_tenant_id or (
        str(user.active_tenant_id)
        if user and hasattr(user, "active_tenant_id") and user.active_tenant_id
        else None
    )
    if not raw_tid:
        # Default developer tenant fallback
        raw_tid = "tenant-alpha-001"

    try:
        return uuid.UUID(str(raw_tid))
    except (ValueError, AttributeError):
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(raw_tid))


# ----------------------------------------------------------------------------
# 1. POST /api/v1/intake/email — REST JSON Webhook
# ----------------------------------------------------------------------------
@router.post(
    "/intake/email",
    response_model=EmailIntakeResponse,
    tags=["Email Intake"],
)
async def intake_email_webhook(
    payload: EmailWebhookRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """REST Webhook accepting JSON email submissions with base64 attachments."""
    tenant_id = resolve_tenant_id(x_tenant_id, current_user)

    # Decode and validate base64 attachments
    parsed_attachments: List[ParsedAttachmentDTO] = []
    for att in payload.attachments or []:
        try:
            att_bytes = base64.b64decode(att.payload_base64)
            if len(att_bytes) > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Attachment '{att.filename}' exceeds maximum allowed size of 10MB",
                )
            parsed_attachments.append(
                ParsedAttachmentDTO(
                    filename=att.filename,
                    content_type=att.content_type,
                    size=len(att_bytes),
                    data=att_bytes,
                    sha256_hash=hashlib.sha256(att_bytes).hexdigest(),
                )
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid base64 attachment data for '{att.filename}': {str(exc)}",
            )

    # Extract case reference token: [CASE-XXXX]
    case_match = CASE_NUMBER_REGEX.search(payload.subject or "")
    case_number_ref = case_match.group(1).upper() if case_match else None

    # Synthesize unique Message-ID if omitted
    msg_id = payload.message_id
    if not msg_id or not msg_id.strip():
        synth_token = hashlib.sha256(
            f"{payload.sender}:{payload.subject}:{datetime.utcnow().isoformat()}".encode("utf-8")
        ).hexdigest()[:12]
        msg_id = f"<webhook-{synth_token}@ckyc.internal>"
    msg_id = msg_id.strip()

    parsed_dto = ParsedEmailDTO(
        message_id=msg_id,
        sender=payload.sender,
        sender_name=None,
        recipient=payload.recipient or "kyc-intake@fintechbank.com",
        subject=payload.subject or "",
        date=datetime.now(timezone.utc),
        body_text=payload.body_text or payload.body or "",
        body_html=None,
        case_number_ref=case_number_ref,
        attachments=parsed_attachments,
        attachment_count=len(parsed_attachments),
    )

    status_result, rec, target_case = await email_intake_service.ingest_parsed_email(
        db=db,
        parsed=parsed_dto,
        tenant_id=tenant_id,
        background_tasks=background_tasks,
    )

    if status_result == "attached_to_case":
        return EmailIntakeResponse(
            status="attached_to_case",
            case_id=str(target_case.id) if target_case else None,
            case_number=target_case.case_number if target_case else None,
            attachments_count=rec.attachment_count,
            message_id=rec.message_id,
        )
    elif status_result == "idempotent_duplicate":
        is_same_tenant = (rec.tenant_id == tenant_id)
        return EmailIntakeResponse(
            status="idempotent_duplicate",
            message_id=rec.message_id,
            case_id=str(target_case.id) if (target_case and is_same_tenant and rec.case_id) else None,
            case_number=target_case.case_number if (target_case and is_same_tenant) else None,
        )
    else:
        return EmailIntakeResponse(
            status="routed_to_exception_queue",
            exception_id=str(rec.id),
            message_id=rec.message_id,
            detail="Unmatched case reference routed to exception queue",
        )


# ----------------------------------------------------------------------------
# 2. POST /api/v1/intake/eml — Raw RFC 822 .eml File Upload
# ----------------------------------------------------------------------------
@router.post(
    "/intake/eml",
    response_model=EmailIntakeResponse,
    tags=["Email Intake"],
)
async def intake_eml_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Raw RFC 822 / MIME .eml file intake endpoint."""
    tenant_id = resolve_tenant_id(x_tenant_id, current_user)
    raw_bytes = await file.read()
    parsed_dto = parse_rfc822_email(raw_bytes)

    status_result, rec, target_case = await email_intake_service.ingest_parsed_email(
        db=db,
        parsed=parsed_dto,
        tenant_id=tenant_id,
        background_tasks=background_tasks,
        raw_eml_bytes=raw_bytes,
    )

    if status_result == "attached_to_case":
        return EmailIntakeResponse(
            status="attached_to_case",
            case_id=str(target_case.id) if target_case else None,
            case_number=target_case.case_number if target_case else None,
            attachments_count=rec.attachment_count,
            message_id=rec.message_id,
        )
    elif status_result == "idempotent_duplicate":
        is_same_tenant = (rec.tenant_id == tenant_id)
        return EmailIntakeResponse(
            status="idempotent_duplicate",
            message_id=rec.message_id,
            case_id=str(target_case.id) if (target_case and is_same_tenant and rec.case_id) else None,
            case_number=target_case.case_number if (target_case and is_same_tenant) else None,
        )
    else:
        return EmailIntakeResponse(
            status="routed_to_exception_queue",
            exception_id=str(rec.id),
            message_id=rec.message_id,
            detail="Unmatched case reference routed to exception queue",
        )


# ----------------------------------------------------------------------------
# 3. GET /api/v1/email/exceptions — List Unmatched Exception Queue
# ----------------------------------------------------------------------------
@router.get(
    "/email/exceptions",
    response_model=EmailExceptionListResponse,
    tags=["Email Exception Queue"],
)
async def list_email_exceptions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: str = Query("unmatched"),
    db: AsyncSession = Depends(get_db),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Query unmatched inbound emails in the tenant exception queue with pagination."""
    tenant_id = resolve_tenant_id(x_tenant_id, current_user)

    # Count total
    count_stmt = select(func.count(MailIngestionRecord.id)).where(
        MailIngestionRecord.tenant_id == tenant_id,
        MailIngestionRecord.status == status,
    )
    total = (await db.execute(count_stmt)).scalar() or 0

    # Fetch paginated items
    stmt = (
        select(MailIngestionRecord)
        .where(
            MailIngestionRecord.tenant_id == tenant_id,
            MailIngestionRecord.status == status,
        )
        .order_by(MailIngestionRecord.received_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = (await db.execute(stmt)).scalars().all()

    return EmailExceptionListResponse(
        items=[EmailExceptionItem.model_validate(it) for it in items],
        total=total,
        limit=limit,
        offset=offset,
    )


# ----------------------------------------------------------------------------
# 4. POST /api/v1/email/exceptions/{id}/assign — Manual Assignment
# ----------------------------------------------------------------------------
@router.post(
    "/email/exceptions/{id}/assign",
    response_model=EmailExceptionAssignResponse,
    tags=["Email Exception Queue"],
)
async def assign_email_exception(
    id: str,
    payload: EmailExceptionAssignRequest,
    background_tasks: Optional[BackgroundTasks] = None,
    db: AsyncSession = Depends(get_db),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Manually assign an unmatched email exception to a target KYC case."""
    tenant_id = resolve_tenant_id(x_tenant_id, current_user)

    try:
        exc_uuid = uuid.UUID(str(id))
        case_uuid = uuid.UUID(str(payload.case_id))
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid UUID format for exception or case",
        )

    exc, case = await email_intake_service.assign_exception_to_case(
        db=db,
        exception_id=exc_uuid,
        target_case_id=case_uuid,
        tenant_id=tenant_id,
        reviewer_id=current_user.id if current_user else None,
        background_tasks=background_tasks,
    )

    return EmailExceptionAssignResponse(
        status="assigned",
        exception_id=str(exc.id),
        case_id=str(case.id),
        case_number=case.case_number,
        attachments_attached=exc.attachment_count,
    )


# ----------------------------------------------------------------------------
# 5. POST /api/v1/email/exceptions/{id}/dismiss — Dismiss Junk Exception
# ----------------------------------------------------------------------------
@router.post(
    "/email/exceptions/{id}/dismiss",
    response_model=EmailExceptionDismissResponse,
    tags=["Email Exception Queue"],
)
async def dismiss_email_exception(
    id: str,
    db: AsyncSession = Depends(get_db),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Dismiss a promotional, spam, or irrelevant email exception."""
    tenant_id = resolve_tenant_id(x_tenant_id, current_user)

    try:
        exc_uuid = uuid.UUID(str(id))
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid exception UUID format",
        )

    exc = await email_intake_service.dismiss_exception(
        db=db,
        exception_id=exc_uuid,
        tenant_id=tenant_id,
        reviewer_id=current_user.id if current_user else None,
    )
    return EmailExceptionDismissResponse(status="dismissed", exception_id=str(exc.id))
