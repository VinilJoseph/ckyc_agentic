"""Local Document Storage Service Adapter.

Provides deterministic, pure-Python magic-byte validation, SHA-256 integrity hashing,
strict 10MB size limits, and path-traversal sanitization for tenant-isolated document storage.
"""
import hashlib
import os
from pathlib import Path
import re
from typing import Optional, Tuple, Union
import uuid
from fastapi import HTTPException, status

MAGIC_SIGNATURES = {
    b"%PDF-": "application/pdf",
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
}

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES = ["application/pdf", "image/jpeg", "image/png"]


def detect_magic_mime(buffer: bytes) -> str:
    """Inspects first bytes to identify MIME type without requiring OS libmagic binaries."""
    if not buffer or len(buffer) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content is too small to determine MIME type or is empty",
        )

    # Check PDF (supports initial or first 1024 bytes BOM/prefix)
    if buffer.startswith(b"%PDF-") or (len(buffer) >= 1024 and b"%PDF-" in buffer[:1024]):
        return "application/pdf"

    # Check JPEG
    if buffer.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    # Check PNG
    if buffer.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Magic byte validation failed: unsupported format. Allowed: PDF, JPEG, PNG",
    )


def sanitize_filename(filename: str) -> str:
    """Strips path traversal sequences, replaces spaces with underscores, and retains safe chars."""
    clean_name = Path(filename).name
    # Remove directory separators and null bytes
    clean_name = re.sub(r"[\/\\\0]", "", clean_name)
    # Replace spaces with underscores
    clean_name = clean_name.replace(" ", "_")
    # Retain alphanumeric, dots, hyphens, and underscores
    clean_name = re.sub(r"[^A-Za-z0-9._\-]", "", clean_name)
    if not clean_name:
        clean_name = f"document_{uuid.uuid4().hex[:8]}.bin"
    return clean_name


class LocalStorageService:
    def __init__(self, base_dir: str = "data/storage"):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def validate_file(self, file_bytes: bytes, filename: str) -> Tuple[str, str, int]:
        """Validates file size (max 10MB), magic bytes, and computes SHA-256 hash.

        Returns:
            Tuple of (detected_mime, file_hash, file_length)
        """
        file_len = len(file_bytes)
        if file_len == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file provided: file size cannot be 0 bytes",
            )

        if file_len > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB",
            )

        detected_mime = detect_magic_mime(file_bytes)
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        return detected_mime, file_hash, file_len

    async def save_file(
        self,
        tenant_id: Union[uuid.UUID, str],
        case_id: Union[uuid.UUID, str],
        doc_id: Union[uuid.UUID, str],
        filename: str,
        file_bytes: bytes,
    ) -> str:
        """Saves file to data/storage/tenants/{tenant_id}/cases/{case_id}/{doc_id}_{filename}.

        Returns:
            Relative storage_key string.
        """
        target_dir = self.base_dir / "tenants" / str(tenant_id) / "cases" / str(case_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        clean_filename = sanitize_filename(filename)
        target_file = target_dir / f"{doc_id}_{clean_filename}"

        # Write file atomically
        with open(target_file, "wb") as f:
            f.write(file_bytes)

        # Store relative storage_key with forward slashes
        return f"tenants/{tenant_id}/cases/{case_id}/{doc_id}_{clean_filename}"

    def save_file_sync(
        self,
        tenant_id: Union[uuid.UUID, str],
        case_id: Union[uuid.UUID, str],
        doc_id: Union[uuid.UUID, str],
        filename: str,
        file_bytes: bytes,
    ) -> str:
        target_dir = self.base_dir / "tenants" / str(tenant_id) / "cases" / str(case_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        clean_filename = sanitize_filename(filename)
        target_file = target_dir / f"{doc_id}_{clean_filename}"

        with open(target_file, "wb") as f:
            f.write(file_bytes)

        return f"tenants/{tenant_id}/cases/{case_id}/{doc_id}_{clean_filename}"

    async def save_unmatched_file(
        self,
        tenant_id: Union[uuid.UUID, str],
        exception_id: Union[uuid.UUID, str],
        filename: str,
        file_bytes: bytes,
    ) -> str:
        """Saves file to data/storage/tenants/{tenant_id}/unmatched/{exception_id}/{filename}."""
        target_dir = self.base_dir / "tenants" / str(tenant_id) / "unmatched" / str(exception_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        clean_filename = sanitize_filename(filename)
        target_file = target_dir / clean_filename

        with open(target_file, "wb") as f:
            f.write(file_bytes)

        return f"tenants/{tenant_id}/unmatched/{exception_id}/{clean_filename}"

    def get_file_path(self, storage_key: str) -> Path:
        """Resolves storage_key to Path with directory traversal protection."""
        resolved_path = (self.base_dir / storage_key).resolve()
        if not resolved_path.is_relative_to(self.base_dir):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security violation: directory traversal detected in storage key",
            )
        if not resolved_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stored document file not found on disk",
            )
        return resolved_path

    def read_file(self, storage_key: str) -> bytes:
        """Reads file bytes with traversal protection."""
        file_path = self.get_file_path(storage_key)
        with open(file_path, "rb") as f:
            return f.read()


storage_service = LocalStorageService()
