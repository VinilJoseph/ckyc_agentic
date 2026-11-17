"""Document Intake & Management Endpoints.

Implements:
- POST /api/v1/cases/{case_id}/documents: Multipart upload, magic-byte validation, SHA-256, storage, audit logging
- GET /api/v1/cases/{case_id}/documents/{doc_id}/preview: Preview metadata and download URL
- GET /api/v1/documents/{id}/download: Secure file streaming with tenant isolation
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import get_current_tenant_id
from app.core.database import get_db, get_scoped_or_404
from app.core.dependencies import get_current_user, get_tenant_context, require_reviewer
from app.models.audit import AuditEvent
from app.models.case import KycCase
from app.models.document import CaseDocument
from app.models.tenant import UsageRecord
from app.models.user import User
from app.schemas.document import CaseDocumentResponse, DocumentPreviewResponse
from app.services.storage.local import storage_service

router = APIRouter()


@router.post("/cases/{case_id}/documents", response_model=CaseDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    case_id: str,
    file: UploadFile = File(...),
    document_type: str = Form("identity_card"),
    current_user: User = Depends(require_reviewer),
    tenant_id: uuid.UUID = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Uploads an identity document with magic-byte validation, SHA-256 calculation, and local disk storage."""
    try:
        case_uuid = uuid.UUID(str(case_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    # 1. Verify case exists and belongs to active tenant
    case = await get_scoped_or_404(db, KycCase, case_uuid, tenant_id=tenant_id)

    # 2. Prevent upload to closed/terminal cases
    if case.status in ("closed", "approved", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot upload documents to a case in '{case.status}' status",
        )

    # 3. Read bytes and run magic bytes and size validation
    file_bytes = await file.read()
    filename = file.filename or "upload.bin"
    mime_type, file_hash, file_size = storage_service.validate_file(file_bytes, filename)

    # 4. Generate unique document ID and persist to local tenant directory
    doc_id = uuid.uuid4()
    storage_key = await storage_service.save_file(
        tenant_id=tenant_id,
        case_id=case_uuid,
        doc_id=doc_id,
        filename=filename,
        file_bytes=file_bytes,
    )

    # 5. Insert CaseDocument database record
    doc = CaseDocument(
        id=doc_id,
        tenant_id=tenant_id,
        case_id=case_uuid,
        document_type=document_type,
        storage_key=storage_key,
        original_filename=filename,
        file_hash=file_hash,
        mime_type=mime_type,
        file_size=file_size,
        source="portal",
        review_status="pending",
    )
    db.add(doc)

    # 6. Emit immutable AuditEvent
    audit_evt = AuditEvent(
        tenant_id=tenant_id,
        actor_id=current_user.id,
        actor_role=current_user.active_role or "reviewer",
        action="document_uploaded",
        resource_type="document",
        resource_id=doc_id,
        metadata_={
            "case_id": str(case_uuid),
            "filename": filename,
            "mime_type": mime_type,
            "file_hash": file_hash,
            "file_size": file_size,
        },
    )
    db.add(audit_evt)

    # 7. Increment tenant usage counter
    stmt = select(UsageRecord).where(
        UsageRecord.tenant_id == tenant_id,
        UsageRecord.metric_name == "documents_uploaded",
    )
    usage = (await db.execute(stmt)).scalar_one_or_none()
    if usage:
        usage.metric_value += 1
    else:
        db.add(UsageRecord(tenant_id=tenant_id, metric_name="documents_uploaded", metric_value=1))

    # Auto-transition case status if still in awaiting_documents
    if case.status == "awaiting_documents":
        case.status = "documents_received"

    await db.flush()

    preview_url = f"/api/v1/cases/{case_uuid}/documents/{doc_id}/preview"
    return CaseDocumentResponse(
        id=doc.id,
        case_id=doc.case_id,
        tenant_id=doc.tenant_id,
        document_type=doc.document_type,
        storage_key=doc.storage_key,
        original_filename=doc.original_filename,
        file_hash=doc.file_hash,
        mime_type=doc.mime_type,
        file_size=doc.file_size,
        source=doc.source,
        review_status=doc.review_status,
        preview_url=preview_url,
        uploaded_at=doc.uploaded_at,
        reviewed_at=doc.reviewed_at,
    )


@router.get("/cases/{case_id}/documents/{doc_id}/preview", response_model=DocumentPreviewResponse)
async def get_document_preview(
    case_id: str,
    doc_id: str,
    current_user: User = Depends(require_reviewer),
    tenant_id: uuid.UUID = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Returns document preview metadata with download link."""
    try:
        case_uuid = uuid.UUID(str(case_id))
        doc_uuid = uuid.UUID(str(doc_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    doc = await get_scoped_or_404(db, CaseDocument, doc_uuid, tenant_id=tenant_id)
    if doc.case_id != case_uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found on specified case",
        )

    download_url = f"/api/v1/documents/{doc_uuid}/download"
    return DocumentPreviewResponse(
        preview_available=True,
        document_id=doc.id,
        mime_type=doc.mime_type,
        filename=doc.original_filename,
        url=download_url,
        storage_key=doc.storage_key,
    )


@router.get("/documents/{id}/download")
async def download_document(
    id: str,
    current_user: User = Depends(require_reviewer),
    tenant_id: uuid.UUID = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Streams stored document bytes with strict tenant scoping."""
    try:
        doc_uuid = uuid.UUID(str(id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    doc = await get_scoped_or_404(db, CaseDocument, doc_uuid, tenant_id=tenant_id)
    file_path = storage_service.get_file_path(doc.storage_key)

    return FileResponse(
        path=str(file_path),
        media_type=doc.mime_type,
        filename=doc.original_filename,
    )
