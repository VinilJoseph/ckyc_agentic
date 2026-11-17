"""Case Schemas: Creation, Transitions, Responses & Hydrated Detail."""
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.schemas.document import CaseDocumentResponse
from app.schemas.verification import ExtractedFieldResponse, SelfieMatchResponse, ValidationIssueResponse


class RepresentativeCreate(BaseModel):
    full_name: str
    role_title: str
    email: Optional[EmailStr] = None


class ApplicantCreate(BaseModel):
    applicant_type: str = "person"  # person | business
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    business_name: Optional[str] = None
    registration_number: Optional[str] = None
    incorporation_date: Optional[date] = None
    representatives: Optional[List[RepresentativeCreate]] = None


class CaseCreate(BaseModel):
    applicant: ApplicantCreate
    purpose: str = Field(..., min_length=1, max_length=500)
    case_type: str = "individual"  # individual | business


class CaseDecisionRequest(BaseModel):
    reason: Optional[str] = None
    review_reason: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_decision_reason(cls, data: Any) -> Any:
        if isinstance(data, dict):
            r = data.get("reason")
            rr = data.get("review_reason")
            chosen = rr if (rr is not None and str(rr).strip()) else r
            if not chosen or not str(chosen).strip():
                raise ValueError("A decision reason must be provided (via 'reason' or 'review_reason')")
            data["reason"] = str(chosen).strip()
            data["review_reason"] = str(chosen).strip()
        return data


class CaseResponse(BaseModel):
    id: Union[uuid.UUID, str]
    tenant_id: Union[uuid.UUID, str]
    applicant_id: Union[uuid.UUID, str]
    case_number: str
    purpose: str
    case_type: str
    status: str
    review_decision: Optional[str] = None
    review_reason: Optional[str] = None
    reason: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CaseListItem(BaseModel):
    id: Union[uuid.UUID, str]
    tenant_id: Union[uuid.UUID, str]
    case_number: str
    purpose: str
    case_type: str
    status: str
    applicant_name: str
    applicant_type: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class CaseTransitionRequest(BaseModel):
    status: str
    reason: Optional[str] = None


class ApplicantDetailResponse(BaseModel):
    id: Union[uuid.UUID, str]
    applicant_type: str
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    business_name: Optional[str] = None
    registration_number: Optional[str] = None
    incorporation_date: Optional[date] = None
    representatives: List[Any] = []


class CaseDetailResponse(BaseModel):
    id: Union[uuid.UUID, str]
    tenant_id: Union[uuid.UUID, str]
    applicant_id: Union[uuid.UUID, str]
    case_number: str
    purpose: str
    case_type: str
    status: str
    reviewer_id: Optional[Union[uuid.UUID, str]] = None
    review_decision: Optional[str] = None
    review_reason: Optional[str] = None
    reason: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    applicant: ApplicantDetailResponse
    document_count: int = 0
    documents: List[CaseDocumentResponse] = []
    extracted_fields: List[ExtractedFieldResponse] = []
    validation_issues: List[ValidationIssueResponse] = []
    selfie_match: Optional[SelfieMatchResponse] = None
    stepper: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
