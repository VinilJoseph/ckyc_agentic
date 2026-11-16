"""Unit tests for RFC 822 / MIME email parsing, CASE tag regex extraction, and attachments."""
import hashlib
import pytest
from fastapi import HTTPException

from app.services.email.parser import (
    CASE_NUMBER_REGEX,
    ParsedEmailDTO,
    parse_rfc822_email,
)


def test_case_number_regex():
    """Verify CASE reference extraction from various subject and body patterns."""
    text1 = "Re: Verification Documents [CASE-1234]"
    match1 = CASE_NUMBER_REGEX.search(text1)
    assert match1 is not None
    assert match1.group(1).upper() == "CASE-1234"

    text2 = "Submission for [case-abc_12] updated"
    match2 = CASE_NUMBER_REGEX.search(text2)
    assert match2 is not None
    assert match2.group(1).upper() == "CASE-ABC_12"

    text3 = "No case tag in this subject"
    assert CASE_NUMBER_REGEX.search(text3) is None


def test_parse_valid_rfc822_email():
    """Verify parsing a valid RFC 822 email payload."""
    raw_email = (
        b"From: John Doe <john@example.com>\r\n"
        b"To: kyc-intake@kycmarket.local\r\n"
        b"Subject: KYC Documents [CASE-8842]\r\n"
        b"Date: Mon, 16 Nov 2026 10:00:00 +0000\r\n"
        b"Message-ID: <msg123@example.com>\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"\r\n"
        b"Hello, here are my KYC documents for [CASE-8842].\r\n"
    )

    dto = parse_rfc822_email(raw_email)
    assert isinstance(dto, ParsedEmailDTO)
    assert dto.sender == "john@example.com"
    assert dto.sender_name == "John Doe"
    assert dto.case_number_ref == "CASE-8842"
    assert "CASE-8842" in dto.body_text
    assert dto.message_id == "<msg123@example.com>"
    assert dto.attachment_count == 0


def test_parse_email_with_attachment():
    """Verify parsing multipart MIME email with file attachment and SHA-256 hash."""
    attachment_content = b"%PDF-1.4 Mock PDF Document Content"
    expected_hash = hashlib.sha256(attachment_content).hexdigest()

    raw_multipart = (
        b"From: applicant@example.com\r\n"
        b"To: kyc-intake@kycmarket.local\r\n"
        b"Subject: Submission [CASE-7777]\r\n"
        b"MIME-Version: 1.0\r\n"
        b"Content-Type: multipart/mixed; boundary=\"BOUNDARY\"\r\n"
        b"\r\n"
        b"--BOUNDARY\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"\r\n"
        b"Attached is my passport.\r\n"
        b"--BOUNDARY\r\n"
        b"Content-Type: application/pdf\r\n"
        b"Content-Disposition: attachment; filename=\"passport.pdf\"\r\n"
        b"\r\n"
        + attachment_content + b"\r\n"
        b"--BOUNDARY--\r\n"
    )

    dto = parse_rfc822_email(raw_multipart)
    assert dto.case_number_ref == "CASE-7777"
    assert dto.attachment_count == 1
    att = dto.attachments[0]
    assert att.filename == "passport.pdf"
    assert att.size == len(attachment_content)
    assert att.sha256_hash == expected_hash


def test_parse_email_missing_headers_raises_400():
    """Verify empty or headerless payload raises HTTP 400."""
    with pytest.raises(HTTPException) as exc_info:
        parse_rfc822_email(b"   \r\n\r\nJust text without headers")
    assert exc_info.value.status_code == 400


def test_parse_email_attachment_exceeds_size_limit():
    """Verify attachment exceeding max size raises HTTP 413."""
    oversized_data = b"X" * (1024 * 1024 + 10)  # > 1MB
    raw_multipart = (
        b"From: test@example.com\r\n"
        b"Subject: Big File\r\n"
        b"Content-Type: multipart/mixed; boundary=\"BOUND\"\r\n"
        b"\r\n"
        b"--BOUND\r\n"
        b"Content-Type: application/octet-stream\r\n"
        b"Content-Disposition: attachment; filename=\"large.bin\"\r\n"
        b"\r\n"
        + oversized_data + b"\r\n"
        b"--BOUND--\r\n"
    )

    # Set ceiling to 1MB (1024 * 1024 bytes)
    with pytest.raises(HTTPException) as exc_info:
        parse_rfc822_email(raw_multipart, max_attachment_size=1024 * 1024)
    assert exc_info.value.status_code == 413
