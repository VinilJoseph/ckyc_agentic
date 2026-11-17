"""PAN (Permanent Account Number) Validation Rules.

Validates Indian Income Tax PAN structure:
- Exactly 10 alphanumeric characters: 5 letters, 4 digits, 1 letter.
- 4th character entity type ('P' for Individual, 'C' for Company, etc.).
- 5th character surname/entity initial consistency.
"""
import re
from typing import Dict, List, Optional, Tuple

PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")

# Indian Taxpayer Entity Categories (4th character)
VALID_ENTITY_TYPES = {
    "P": "Individual / Person",
    "C": "Company",
    "H": "Hindu Undivided Family (HUF)",
    "F": "Partnership Firm / LLP",
    "A": "Association of Persons (AOP)",
    "T": "Trust",
    "B": "Body of Individuals (BOI)",
    "L": "Local Authority",
    "J": "Artificial Juridical Person",
    "G": "Government Agency",
}


def validate_pan(
    pan_str: str,
    applicant_type: Optional[str] = None,
    surname: Optional[str] = None,
    full_name: Optional[str] = None,
) -> Tuple[bool, List[Dict[str, str]]]:
    """Validates PAN format, 4th character entity type, and 5th character initial.

    Returns:
        Tuple of (is_valid: bool, issues: List[Dict[str, str]])
    """
    issues = []
    if not pan_str:
        issues.append({
            "code": "PAN_MISSING",
            "field_name": "pan_number",
            "severity": "ERROR",
            "message": "PAN number is required",
        })
        return False, issues

    normalized_pan = str(pan_str).strip().upper()

    if not PAN_REGEX.match(normalized_pan):
        issues.append({
            "code": "INVALID_PAN_ENTITY_TYPE",
            "field_name": "pan_number",
            "severity": "ERROR",
            "message": f"PAN '{normalized_pan}' does not match standard 10-character alphanumeric format (5 letters, 4 digits, 1 letter)",
        })
        return False, issues

    entity_char = normalized_pan[3]
    if entity_char not in VALID_ENTITY_TYPES:
        issues.append({
            "code": "INVALID_PAN_ENTITY_TYPE",
            "field_name": "pan_number",
            "severity": "ERROR",
            "message": f"PAN 4th character '{entity_char}' is not a valid Indian taxpayer entity type",
        })

    # Cross-validate entity type against applicant profile
    if applicant_type:
        app_type = applicant_type.lower()
        if app_type in ("person", "individual"):
            if entity_char != "P":
                issues.append({
                    "code": "INVALID_PAN_ENTITY_TYPE",
                    "field_name": "pan_number",
                    "severity": "ERROR",
                    "message": f"PAN 4th character '{entity_char}' does not match applicant type 'person' (expected 'P')",
                })
        elif app_type in ("business", "company", "corporate"):
            if entity_char not in ("C", "F", "T", "A", "H", "B"):
                issues.append({
                    "code": "INVALID_PAN_ENTITY_TYPE",
                    "field_name": "pan_number",
                    "severity": "ERROR",
                    "message": f"PAN 4th character '{entity_char}' does not match corporate/business entity",
                })

    # Validate 5th character against applicant surname initial
    expected_initial = None
    if surname and surname.strip():
        expected_initial = surname.strip()[0].upper()
    elif full_name and full_name.strip():
        tokens = [t for t in full_name.strip().split() if t]
        if tokens:
            expected_initial = tokens[-1][0].upper()

    if expected_initial:
        pan_initial = normalized_pan[4]
        if pan_initial != expected_initial:
            issues.append({
                "code": "PAN_SURNAME_MISMATCH",
                "field_name": "pan_number",
                "severity": "WARNING",
                "message": f"PAN 5th character '{pan_initial}' does not match applicant surname initial '{expected_initial}'",
            })

    has_errors = any(i["severity"] == "ERROR" for i in issues)
    return not has_errors, issues
