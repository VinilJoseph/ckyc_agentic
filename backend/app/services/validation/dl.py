"""Indian Driver's License (MoRTH) Validation Rules.

Validates Indian Driver's License format:
- 2-letter Indian State / UT code (across 36 valid codes).
- 2-digit RTO code (01-99).
- 4-digit issue year (1960 <= year <= current year).
- 7-digit unique sequential number.
- Minimum legal age at issuance (>= 18 years old).
"""
from datetime import date, datetime
import re
from typing import Dict, List, Optional, Tuple

INDIAN_STATE_CODES = {
    "AN", "AP", "AR", "AS", "BR", "CH", "CG", "DN", "DD", "DL",
    "GA", "GJ", "HR", "HP", "JK", "JH", "KA", "KL", "LA", "LD",
    "MP", "MH", "MN", "ML", "MZ", "NL", "OD", "PY", "PB", "RJ",
    "SK", "TN", "TS", "TR", "UP", "UK", "WB", "UA", "OR"
}

DL_REGEX = re.compile(r"^([A-Z]{2})[- ]?([0-9]{2})[- ]?([0-9]{4})[- ]?([0-9]{7})$")


def validate_drivers_license(
    dl_number: str,
    applicant_dob: Optional[date] = None,
) -> Tuple[bool, List[Dict[str, str]]]:
    """Validates DL format, state code, issue year, and age at issuance.

    Returns:
        Tuple of (is_valid: bool, issues: List[Dict[str, str]])
    """
    issues = []
    if not dl_number:
        issues.append({
            "code": "DL_MISSING",
            "field_name": "dl_number",
            "severity": "ERROR",
            "message": "Driver's License number is missing",
        })
        return False, issues

    normalized = str(dl_number).strip().upper()
    match = DL_REGEX.match(normalized)
    if not match:
        issues.append({
            "code": "INVALID_DL_FORMAT",
            "field_name": "dl_number",
            "severity": "ERROR",
            "message": f"Driver's License '{normalized}' does not match standard MoRTH format (SS-RR-YYYY-NNNNNNN)",
        })
        return False, issues

    state_code, rto_code, issue_year_str, _ = match.groups()

    if state_code not in INDIAN_STATE_CODES:
        issues.append({
            "code": "INVALID_DL_FORMAT",
            "field_name": "dl_number",
            "severity": "ERROR",
            "message": f"Invalid Indian state code '{state_code}' in Driver's License",
        })

    issue_year = int(issue_year_str)
    current_year = datetime.now().year
    if issue_year < 1960 or issue_year > current_year:
        issues.append({
            "code": "INVALID_DL_FORMAT",
            "field_name": "dl_number",
            "severity": "ERROR",
            "message": f"Driver's License issue year {issue_year} is out of valid range (1960-{current_year})",
        })

    if applicant_dob:
        age_at_issue = issue_year - applicant_dob.year
        if age_at_issue < 18:
            issues.append({
                "code": "DL_UNDERAGE_ISSUE",
                "field_name": "dl_number",
                "severity": "ERROR",
                "message": f"Driver's License was issued when applicant was {age_at_issue} years old (under statutory minimum of 18)",
            })

    is_valid = not any(i["severity"] == "ERROR" for i in issues)
    return is_valid, issues
