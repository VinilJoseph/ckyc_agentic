"""Pydantic Schemas for Email Intake & Email Exception Queue (Milestone 3)."""
from datetime import datetime
from typing import Any, List, Optional, Union
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator


class EmailAttachmentPayload(BaseModel):
    """Attachment payload for JSON webhook intake."""
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(default="application/octet-stream", max_length=100)
    payload_base64: str = Field(..., description="Base64-encoded attachment byte content")


class EmailWebhookRequest(BaseModel):
    """Request payload for POST /api/v1/intake/email webhook."""
    message_id: Optional[str] = Field(default=None, max_length=255)
    sender: str = Field(..., min_length=1, max_length=255)
    recipient: Optional[str] = Field(default="kyc-intake@fintechbank.com", max_length=255)
    subject: str = Field(default="", max_length=500)
    body: Optional[str] = None
    body_text: Optional[str] = None
    attachments: Optional[List[EmailAttachmentPayload]] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def sync_body_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            b = data.get("body")
            bt = data.get("body_text")
            if b and not bt:
                data["body_text"] = b
            elif bt and not b:
                data["body"] = bt
        return data


# Alias for backward and cross-contract compatibility
EmailWebhookPayload = EmailWebhookRequest


class EmailIntakeResponse(BaseModel):
    """Unified response model for email intake endpoints (/intake/email and /intake/eml)."""
    status: str = Field(
        ...,
        description="attached_to_case | routed_to_exception_queue | idempotent_duplicate",
    )
    case_id: Optional[Union[uuid.UUID, str]] = None
    case_number: Optional[str] = None
    exception_id: Optional[Union[uuid.UUID, str]] = None
    attachments_count: Optional[int] = 0
    message_id: Optional[str] = None
    detail: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EmailExceptionItem(BaseModel):
    """Represents a single email exception in the compliance triage queue."""
    id: Union[uuid.UUID, str]
    tenant_id: Optional[Union[uuid.UUID, str]] = None
    message_id: str
    sender: str
    recipient: Optional[str] = "kyc-intake@fintechbank.com"
    subject: str = ""
    body_text: Optional[str] = None
    status: str = "unmatched"  # unmatched | assigned | dismissed
    case_id: Optional[Union[uuid.UUID, str]] = None
    attachment_count: int = 0
    error_message: Optional[str] = None
    received_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Alias for interface contract parity
MailIngestionRecordRead = EmailExceptionItem


class EmailExceptionListResponse(BaseModel):
    """Paginated response for GET /api/v1/email/exceptions."""
    items: List[EmailExceptionItem]
    total: int
    limit: Optional[int] = 50
    offset: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class EmailExceptionAssignRequest(BaseModel):
    """Request payload for POST /api/v1/email/exceptions/{id}/assign."""
    case_id: Union[uuid.UUID, str] = Field(..., description="Target KycCase UUID or string ID")


class EmailExceptionAssignResponse(BaseModel):
    """Response returned upon assigning an exception to a KYC case."""
    status: str = "assigned"
    exception_id: Union[uuid.UUID, str]
    case_id: Union[uuid.UUID, str]
    case_number: Optional[str] = None
    attachments_attached: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class EmailExceptionDismissResponse(BaseModel):
    """Response returned upon dismissing a junk email exception."""
    status: str = "dismissed"
    exception_id: Union[uuid.UUID, str]

    model_config = ConfigDict(from_attributes=True)
