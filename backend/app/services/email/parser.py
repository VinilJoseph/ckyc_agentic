"""RFC 822 & MIME Email Parser using Python Standard Library.

Compliant with RFC 822, RFC 2047, RFC 2231, and RFC 2045:
- Uses email.message_from_bytes with policy.default
- Multipart walking and body extraction (plain with HTML fallback)
- Attachment extraction, size ceiling check (10MB limit -> HTTP 413)
- SHA-256 calculation per attachment
- Malformed header validation (missing essential headers -> HTTP 400)
- Regex extraction of [CASE-XXXX] reference tokens
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import email
from email import policy
import email.utils
import hashlib
import re
from typing import Any, List, Optional
from fastapi import HTTPException, status


@dataclass
class ParsedAttachmentDTO:
    filename: str
    content_type: str
    size: int
    data: bytes
    sha256_hash: str


@dataclass
class ParsedEmailDTO:
    message_id: str
    sender: str
    sender_name: Optional[str]
    recipient: str
    subject: str
    date: datetime
    body_text: str
    body_html: Optional[str]
    case_number_ref: Optional[str]
    attachments: List[ParsedAttachmentDTO]
    attachment_count: int


CASE_NUMBER_REGEX = re.compile(r"\[(CASE-[A-Za-z0-9_\-]+)\]", re.IGNORECASE)
MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def parse_rfc822_email(
    raw_bytes: bytes, max_attachment_size: int = MAX_ATTACHMENT_SIZE_BYTES
) -> ParsedEmailDTO:
    """Parses raw RFC 822 / MIME bytes into a structured DTO.

    Validates:
    1. Basic RFC 822 presence and required headers.
    2. Decodes RFC 2047 header encodings and RFC 2231 filename parameters.
    3. Traverses multipart structures extracting plain text and HTML fallback.
    4. Enforces 10MB per-attachment size ceiling (HTTP 413).
    """
    if not raw_bytes or len(raw_bytes.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed .eml payload: empty email stream",
        )

    try:
        msg = email.message_from_bytes(raw_bytes, policy=policy.default)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed .eml payload: {str(exc)}",
        )

    # Header extraction
    subject_raw = msg.get("Subject")
    from_raw = msg.get("From")
    to_raw = msg.get("To")
    msg_id_raw = msg.get("Message-ID")
    date_raw = msg.get("Date")

    # Validate essential RFC 822 presence
    if not from_raw and not subject_raw and not msg_id_raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed .eml payload: missing basic RFC 822 headers",
        )

    subject = str(subject_raw or "")
    from_header = str(from_raw or "")
    to_header = str(to_raw or "")
    msg_id = str(msg_id_raw or "")

    # Parse sender email and display name
    sender_name, sender_email = email.utils.parseaddr(from_header)
    clean_sender = sender_email or from_header or "unknown@domain.local"

    # Synthesize fallback Message-ID if missing
    if not msg_id or not msg_id.strip():
        content_hash = hashlib.sha256(raw_bytes).hexdigest()[:16]
        msg_id = f"<generated-{content_hash}@ckyc.internal>"
    msg_id = msg_id.strip()

    # Parse Date
    parsed_date = datetime.now(timezone.utc)
    if date_raw:
        try:
            parsed_date = email.utils.parsedate_to_datetime(str(date_raw))
        except Exception:
            parsed_date = datetime.now(timezone.utc)

    # Extract case reference token: [CASE-XXXX]
    case_match = CASE_NUMBER_REGEX.search(subject)
    case_number_ref = case_match.group(1).upper() if case_match else None

    # Walk MIME tree
    body_plain_parts: List[str] = []
    body_html_parts: List[str] = []
    attachments: List[ParsedAttachmentDTO] = []

    if msg.is_multipart():
        for part in msg.walk():
            content_disposition = str(part.get_content_disposition() or "").lower()
            content_type = part.get_content_type()
            filename = part.get_filename()

            is_attachment = content_disposition == "attachment" or (
                filename is not None and content_type not in ("text/plain", "text/html")
            )

            if is_attachment:
                att_data = part.get_payload(decode=True)
                if not att_data:
                    continue
                if len(att_data) > max_attachment_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Attachment '{filename or 'file'}' exceeds maximum allowed size of 10MB",
                    )
                safe_name = filename or f"attachment_{len(attachments) + 1}.bin"
                att_hash = hashlib.sha256(att_data).hexdigest()
                attachments.append(
                    ParsedAttachmentDTO(
                        filename=safe_name,
                        content_type=content_type or "application/octet-stream",
                        size=len(att_data),
                        data=att_data,
                        sha256_hash=att_hash,
                    )
                )
            elif content_type == "text/plain" and not content_disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body_plain_parts.append(payload.decode(charset, errors="replace"))
            elif content_type == "text/html" and not content_disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body_html_parts.append(payload.decode(charset, errors="replace"))
    else:
        content_type = msg.get_content_type()
        filename = msg.get_filename()
        content_disposition = str(msg.get_content_disposition() or "").lower()

        if content_disposition == "attachment" or filename:
            att_data = msg.get_payload(decode=True)
            if att_data:
                if len(att_data) > max_attachment_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Attachment '{filename or 'file'}' exceeds maximum allowed size of 10MB",
                    )
                safe_name = filename or "attachment_1.bin"
                attachments.append(
                    ParsedAttachmentDTO(
                        filename=safe_name,
                        content_type=content_type or "application/octet-stream",
                        size=len(att_data),
                        data=att_data,
                        sha256_hash=hashlib.sha256(att_data).hexdigest(),
                    )
                )
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")
                if content_type == "text/html":
                    body_html_parts.append(decoded)
                else:
                    body_plain_parts.append(decoded)

    body_text = "\n".join(body_plain_parts).strip()
    if not body_text and body_html_parts:
        raw_html = "\n".join(body_html_parts)
        body_text = re.sub(r"<[^>]+>", " ", raw_html).strip()

    body_html = "\n".join(body_html_parts).strip() if body_html_parts else None

    return ParsedEmailDTO(
        message_id=msg_id,
        sender=clean_sender,
        sender_name=sender_name or None,
        recipient=to_header or "kyc-intake@fintechbank.com",
        subject=subject,
        date=parsed_date,
        body_text=body_text,
        body_html=body_html,
        case_number_ref=case_number_ref,
        attachments=attachments,
        attachment_count=len(attachments),
    )


def parse_email_intake(raw_bytes: bytes, is_eml: bool = True) -> ParsedEmailDTO:
    """Interface contract adapter for email intake parsing."""
    return parse_rfc822_email(raw_bytes)
