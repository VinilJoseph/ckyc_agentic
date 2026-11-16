"""Rule-Based KYC Criteria Validation Engine Aggregator.

Orchestrates all algorithmic verification checks:
- Aadhaar Verhoeff D5 dihedral checksum & masked UIDAI format
- Income Tax PAN structure & entity/surname initial consistency
- Passport MRZ ICAO Doc 9303 7-3-1 modulo 10 checksums
- Indian Driver's License MoRTH state codes & minimum issue age
- Applicant statutory adulthood (age >= 18) & document expiration
- Levenshtein / Token Sort fuzzy name matching
"""
from datetime import date
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.services.validation.demographics import parse_flexible_date, validate_demographics
from app.services.validation.dl import validate_drivers_license
from app.services.validation.fuzzy_matching import validate_name_match
from app.services.validation.mrz import parse_and_validate_mrz
from app.services.validation.pan import validate_pan
from app.services.validation.verhoeff import validate_aadhaar_rules


class ValidationIssueItem(BaseModel):
    code: str
    field_name: str
    severity: str  # ERROR | WARNING | INFO
    message: str


class ValidationResult(BaseModel):
    is_valid: bool
    error_count: int
    warning_count: int
    issues: List[ValidationIssueItem]
    recommendation: str  # APPROVE | REQUIRES_MANUAL_REVIEW | REJECT


class KYCValidationEngine:
    def validate(
        self,
        aadhaar_number: Optional[str] = None,
        pan_number: Optional[str] = None,
        passport_mrz: Optional[str] = None,
        dl_number: Optional[str] = None,
        date_of_birth: Optional[str] = None,
        expiry_date: Optional[str] = None,
        applicant_name: Optional[str] = None,
        extracted_name: Optional[str] = None,
        applicant_type: Optional[str] = "person",
        surname: Optional[str] = None,
    ) -> ValidationResult:
        """Executes full rule suite across supplied KYC criteria and demographic fields."""
        issues: List[ValidationIssueItem] = []

        # 1. Aadhaar Verhoeff Dihedral D5 Check
        if aadhaar_number:
            is_valid_aadhaar, code, msg = validate_aadhaar_rules(aadhaar_number)
            if not is_valid_aadhaar and code and msg:
                issues.append(
                    ValidationIssueItem(
                        code=code,
                        field_name="aadhaar_number",
                        severity="ERROR",
                        message=msg,
                    )
                )

        # 2. PAN Format, Entity Type & Surname Initial
        if pan_number:
            _, pan_issues = validate_pan(
                pan_number,
                applicant_type=applicant_type,
                surname=surname,
                full_name=applicant_name,
            )
            for iss in pan_issues:
                issues.append(
                    ValidationIssueItem(
                        code=iss["code"],
                        field_name=iss["field_name"],
                        severity=iss["severity"],
                        message=iss["message"],
                    )
                )

        # 3. Passport MRZ 7-3-1 Modulo 10 Checksum
        if passport_mrz:
            _, _, mrz_issues = parse_and_validate_mrz(passport_mrz)
            for iss in mrz_issues:
                issues.append(
                    ValidationIssueItem(
                        code=iss["code"],
                        field_name=iss["field_name"],
                        severity=iss["severity"],
                        message=iss["message"],
                    )
                )

        # 4. Driver's License State & Issue Age
        dob_date = parse_flexible_date(date_of_birth) if date_of_birth else None
        if dl_number:
            _, dl_issues = validate_drivers_license(dl_number, applicant_dob=dob_date)
            for iss in dl_issues:
                issues.append(
                    ValidationIssueItem(
                        code=iss["code"],
                        field_name=iss["field_name"],
                        severity=iss["severity"],
                        message=iss["message"],
                    )
                )

        # 5. Demographics (Age >= 18 & Expiry)
        if date_of_birth or expiry_date:
            _, demo_issues = validate_demographics(date_of_birth, expiry_date)
            for iss in demo_issues:
                issues.append(
                    ValidationIssueItem(
                        code=iss["code"],
                        field_name=iss["field_name"],
                        severity=iss["severity"],
                        message=iss["message"],
                    )
                )

        # 6. Fuzzy Name Matching
        if applicant_name and extracted_name:
            _, _, name_issues = validate_name_match(applicant_name, extracted_name)
            for iss in name_issues:
                issues.append(
                    ValidationIssueItem(
                        code=iss["code"],
                        field_name=iss["field_name"],
                        severity=iss["severity"],
                        message=iss["message"],
                    )
                )

        error_count = sum(1 for i in issues if i.severity == "ERROR")
        warning_count = sum(1 for i in issues if i.severity == "WARNING")
        is_valid = error_count == 0

        if error_count > 0:
            recommendation = "REJECT"
        elif warning_count > 0:
            recommendation = "REQUIRES_MANUAL_REVIEW"
        else:
            recommendation = "APPROVE"

        return ValidationResult(
            is_valid=is_valid,
            error_count=error_count,
            warning_count=warning_count,
            issues=issues,
            recommendation=recommendation,
        )


validation_engine = KYCValidationEngine()
