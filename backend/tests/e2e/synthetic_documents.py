"""
Synthetic Document Fixtures for CKYC / eKYC Testing.

Provides in-memory synthetic documents adhering to strict file formats and magic-byte specifications:
1. Valid PDF in-memory bytes (%PDF-1.4 header, xref table, font, stream, trailer).
2. Valid JPEG in-memory bytes (\\xFF\\xD8\\xFF SOI and JFIF header, terminating with \\xFF\\xD9 EOI).
3. Valid PNG in-memory bytes (\\x89PNG\\r\\n\\x1a\\n signature and valid IHDR/IDAT/IEND chunks).
4. Spoofed documents (plain text lacking magic bytes).
5. Oversized binary documents (> 10MB boundary).
"""

import binascii
import struct
import zlib
from typing import Optional


# ============================================================================
# 1. Valid PDF Generator
# ============================================================================

def generate_valid_pdf(text_content: Optional[str] = None) -> bytes:
    """
    Generates a valid, well-formed in-memory PDF document (%PDF-1.4).
    """
    text = text_content or "CKYC Verification Document\nIdentity Verified"
    safe_lines = [line.replace("(", r"\(").replace(")", r"\)") for line in text.splitlines()]

    stream_lines = ["BT", "/F1 12 Tf", "50 750 Td", "14 TL"]
    for i, line in enumerate(safe_lines):
        if i == 0:
            stream_lines.append(f"({line}) Tj")
        else:
            stream_lines.append(f"T* ({line}) Tj")
    stream_lines.append("ET")
    stream_data = "\n".join(stream_lines).encode("latin1")
    stream_len = len(stream_data)

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"

    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = (
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    )
    obj4 = (
        f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode("latin1")
        + stream_data
        + b"\nendstream\nendobj\n"
    )
    obj5 = b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"

    objects = [obj1, obj2, obj3, obj4, obj5]

    offsets = []
    current_offset = len(header)
    for obj in objects:
        offsets.append(current_offset)
        current_offset += len(obj)

    xref_offset = current_offset
    xref = b"xref\n0 6\n0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode("latin1")

    trailer = (
        f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin1")
    )

    pdf_bytes = header + b"".join(objects) + xref + trailer
    assert pdf_bytes.startswith(b"%PDF-1.4"), "PDF must start with %PDF-1.4 magic bytes"
    assert pdf_bytes.strip().endswith(b"%%EOF"), "PDF must end with %%EOF marker"
    return pdf_bytes


# ============================================================================
# 2. Valid JPEG Generator
# ============================================================================

_MINIMAL_VALID_JPEG = bytes([
    0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
    0x01, 0x01, 0x00, 0x48, 0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
    0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
    0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
    0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
    0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
    0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
    0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
    0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
    0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
    0x09, 0x0A, 0x0B, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F,
    0x00, 0xBF, 0x80, 0xFF, 0xD9
])


def generate_valid_jpeg(width: int = 1, height: int = 1) -> bytes:
    """Returns valid JPEG image binary bytes with SOI and EOI."""
    assert _MINIMAL_VALID_JPEG.startswith(b"\xff\xd8\xff"), "JPEG must start with SOI \\xFF\\xD8\\xFF"
    assert _MINIMAL_VALID_JPEG.endswith(b"\xff\xd9"), "JPEG must end with EOI \\xFF\\xD9"
    return _MINIMAL_VALID_JPEG


# ============================================================================
# 3. Valid PNG Generator
# ============================================================================

def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """Formats a standard PNG chunk with length, type, data, and CRC32."""
    length = struct.pack(">I", len(data))
    type_and_data = chunk_type + data
    crc = struct.pack(">I", binascii.crc32(type_and_data) & 0xFFFFFFFF)
    return length + type_and_data + crc


def generate_valid_png(width: int = 8, height: int = 8, color: tuple = (100, 150, 200)) -> bytes:
    """Generates a valid PNG image byte array in pure Python."""
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_chunk = _png_chunk(b"IHDR", ihdr_data)

    r, g, b = color
    scanline = b"\x00" + bytes([r, g, b] * width)
    raw_data = scanline * height

    compressed = zlib.compress(raw_data)
    idat_chunk = _png_chunk(b"IDAT", compressed)
    iend_chunk = _png_chunk(b"IEND", b"")

    png_bytes = signature + ihdr_chunk + idat_chunk + iend_chunk
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n"), "PNG must begin with standard signature"
    return png_bytes


# ============================================================================
# 4. Spoofed Document Generator (Magic-Byte Failure)
# ============================================================================

def generate_spoofed_document(target_extension: str = "pdf") -> bytes:
    """Generates a mock document consisting of plain text disguised with a PDF or JPEG filename."""
    return (
        f"This is a plain text file pretending to be a .{target_extension} file.\n"
        "It lacks magic bytes: %PDF-1.4, \\xFF\\xD8\\xFF, or \\x89PNG.\n"
        "Security validation should reject this file with HTTP 400."
    ).encode("utf-8")


# ============================================================================
# 5. Oversized Binary Document Generator (> 10MB Boundary)
# ============================================================================

def generate_oversized_document(size_mb: int = 11) -> bytes:
    """Generates an in-memory byte buffer exceeding the 10MB upload limit."""
    target_bytes = size_mb * 1024 * 1024
    prefix = b"%PDF-1.4\n%oversized-test-file\n"
    padding_needed = max(0, target_bytes - len(prefix))
    return prefix + (b"X" * padding_needed)
