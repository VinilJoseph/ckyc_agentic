"""
Synthetic Email Fixtures for CKYC / eKYC Testing.

Provides RFC 822 .eml email generation and parsing helpers:
1. Valid RFC 822 .eml with [CASE-XXXX] in Subject, headers, and attachments.
2. Unmatched .eml payload (no case reference) for Email Exception Queue testing.
3. Attachment generation and MIME structure verification.
"""

import email
import email.utils
import re
from email.message import EmailMessage
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple

try:
    from .synthetic_documents import generate_valid_jpeg, generate_valid_pdf
except ImportError:
    try:
        from synthetic_documents import generate_valid_jpeg, generate_valid_pdf
    except ImportError:
        from backend.tests.e2e.synthetic_documents import generate_valid_jpeg, generate_valid_pdf


def generate_synthetic_eml(
    case_number: Optional[str] = "CASE-1001",
    sender: str = "applicant.aarav@example.com",
    recipient: str = "kyc-intake@fintechbank.com",
    subject_prefix: str = "Re: Verification Documents Submission",
    body_text: Optional[str] = None,
    attachments: Optional[List[Tuple[str, bytes, str]]] = None,
    message_id: Optional[str] = None
) -> bytes:
    """
    Constructs a standards-compliant RFC 822 MIME multipart email message (.eml).
    """
    msg = MIMEMultipart()

    if case_number:
        clean_case = case_number.strip().upper()
        if not clean_case.startswith("[") and not clean_case.endswith("]"):
            case_tag = f"[{clean_case}]"
        else:
            case_tag = clean_case
        subject = f"{subject_prefix} {case_tag}"
    else:
        subject = subject_prefix

    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = message_id or email.utils.make_msgid(domain="fintechbank.com")
    msg["MIME-Version"] = "1.0"

    body = body_text or (
        "Dear Verification Team,\n\n"
        "Please find attached my identity verification documents for the CKYC case.\n\n"
        "Regards,\n"
        "Applicant"
    )
    msg.attach(MIMEText(body, "plain", "utf-8"))

    if attachments is None:
        doc_pdf = generate_valid_pdf("Aadhaar Card - Aarav Sharma")
        selfie_jpg = generate_valid_jpeg()
        attachments = [
            ("aadhaar_card.pdf", doc_pdf, "application/pdf"),
            ("selfie_photo.jpg", selfie_jpg, "image/jpeg"),
        ]

    for filename, data, mime_type in attachments:
        maintype, _, subtype = mime_type.partition("/")
        if maintype == "application" and subtype == "pdf":
            part = MIMEApplication(data, _subtype="pdf")
        elif maintype == "image":
            part = MIMEImage(data, _subtype=subtype)
        else:
            part = MIMEApplication(data, _subtype=subtype or "octet-stream")

        part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        msg.attach(part)

    return msg.as_bytes()


def generate_unmatched_eml(
    sender: str = "unregistered.partner@externalsupplier.com",
    recipient: str = "kyc-intake@fintechbank.com",
    subject: str = "Inbound Documents from Partner Entity",
    attachments: Optional[List[Tuple[str, bytes, str]]] = None
) -> bytes:
    """
    Generates a valid .eml message that deliberately contains NO case number reference.
    """
    return generate_synthetic_eml(
        case_number=None,
        sender=sender,
        recipient=recipient,
        subject_prefix=subject,
        body_text="Here are our compliance documents. Case reference is pending.",
        attachments=attachments
    )


def parse_synthetic_eml(eml_bytes: bytes) -> Dict[str, Any]:
    """
    Parses raw RFC 822 .eml bytes back into a structured dictionary.
    """
    msg = email.message_from_bytes(eml_bytes)

    subject = msg.get("Subject", "")
    sender = msg.get("From", "")
    recipient = msg.get("To", "")
    date_header = msg.get("Date", "")
    message_id = msg.get("Message-ID", "")

    case_match = re.search(r"\[(CASE-[A-Za-z0-9_\-]+)\]", subject, re.IGNORECASE)
    case_number_ref = case_match.group(1).upper() if case_match else None

    body_text = ""
    attachments = []

    for part in msg.walk():
        content_disposition = str(part.get("Content-Disposition", ""))
        content_type = part.get_content_type()

        if "attachment" in content_disposition:
            filename = part.get_filename() or "attachment.bin"
            payload = part.get_payload(decode=True)
            attachments.append({
                "filename": filename,
                "mime_type": content_type,
                "size": len(payload) if payload else 0,
                "data": payload
            })
        elif content_type == "text/plain" and not body_text:
            payload = part.get_payload(decode=True)
            if payload:
                body_text = payload.decode("utf-8", errors="replace")

    return {
        "subject": subject,
        "sender": sender,
        "recipient": recipient,
        "date": date_header,
        "message_id": message_id,
        "case_number_ref": case_number_ref,
        "body_text": body_text,
        "attachments": attachments,
        "attachment_count": len(attachments),
    }
