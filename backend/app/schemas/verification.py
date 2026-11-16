"""Verification Schemas for OCR Extraction, KYC Validation, Biometrics & Reviewer Decisions."""
from datetime import datetime
from typing import Any, List, Optional, Union
import uuid
from pydantic import BaseModel, ConfigDict


class ExtractedFieldResponse(BaseModel):
    id: Union[uuid.UUID, str]
    case_id: Optional[Union[uuid.UUID, str]] = None
    tenant_id: Optional[Union[uuid.UUID, str]] = None
    document_id: Optional[Union[uuid.UUID, str]] = None
    field_name: str
    draft_value: Optional[str] = None
    confirmed_value: Optional[str] = None
    source_page: Optional[int] = 1
    confidence: Optional[float] = 1.0
    applicant_confirmed: bool = False
    reviewer_decision: Optional[str] = "pending"
    reviewer_notes: Optional[str] = None
    correction_history: Optional[List[Any]] = []

    model_config = ConfigDict(from_attributes=True)


class DocumentExtractionRequest(BaseModel):
    document_type: str = "aadhaar"
    document_text: Optional[str] = None
    document_id: Optional[Union[uuid.UUID, str]] = None


class DocumentExtractionResponse(BaseModel):
    count: int
    fallback_applied: bool = False
    extracted_fields: List[ExtractedFieldResponse]


class ValidationIssueResponse(BaseModel):
    code: str
    field_name: str
    severity: str  # ERROR | WARNING | INFO
    message: str


class KYCValidationRequest(BaseModel):
    aadhaar_number: Optional[str] = None
    pan_number: Optional[str] = None
    passport_mrz: Optional[str] = None
    dl_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    expiry_date: Optional[str] = None
    applicant_name: Optional[str] = None
    extracted_name: Optional[str] = None


class KYCValidationResponse(BaseModel):
    is_valid: bool
    issues: List[ValidationIssueResponse] = []
    error_count: int = 0
    warning_count: int = 0
    issue_count: int = 0
    recommendation: str = "APPROVE"


class SelfieMatchResponse(BaseModel):
    case_id: Optional[str] = None
    is_match: bool
    confidence: float
    threshold: Optional[float] = 0.75
    method: str = "histogram_correlation"
    details: str = "Biometric facial comparison completed"


class FieldDecisionRequest(BaseModel):
    reviewer_decision: str  # confirmed | corrected | rejected
    corrected_value: Optional[str] = None
    reviewer_notes: Optional[str] = None
