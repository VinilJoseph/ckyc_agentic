"""Email service package exports."""
from app.services.email.parser import (
    ParsedAttachmentDTO,
    ParsedEmailDTO,
    parse_email_intake,
    parse_rfc822_email,
)
from app.services.email.service import EmailIntakeService, email_intake_service

__all__ = [
    "ParsedAttachmentDTO",
    "ParsedEmailDTO",
    "parse_rfc822_email",
    "parse_email_intake",
    "EmailIntakeService",
    "email_intake_service",
]
