"""Document Schemas for Upload, Preview, and Retrieval."""
from datetime import datetime
from typing import Optional, Union
import uuid
from pydantic import BaseModel, ConfigDict


class CaseDocumentResponse(BaseModel):
    id: Union[uuid.UUID, str]
    case_id: Union[uuid.UUID, str]
    tenant_id: Union[uuid.UUID, str]
    document_type: str
    storage_key: str
    original_filename: str
    file_hash: str
    mime_type: str
    file_size: int
    source: str = "portal"
    review_status: str = "pending"
    preview_url: Optional[str] = None
    uploaded_at: datetime
    reviewed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentPreviewResponse(BaseModel):
    preview_available: bool
    document_id: Union[uuid.UUID, str]
    mime_type: str
    filename: str
    url: str
    storage_key: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
