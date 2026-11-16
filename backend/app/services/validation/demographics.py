"""Demographic & Document Expiry Validation Rules.

Validates:
- Applicant Date of Birth (sanity, future dates, statutory adult age >= 18).
- Document Expiration (expired vs expiring within 90 days warning).
"""
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union


def parse_flexible_date(date_val: Union[str, date, datetime]) -> Optional[date]:
    """Parses various date representations into a standard datetime.date object."""
    if not date_val:
        return None
    if isinstance(date_val, datetime):
        return date_val.date()
    if isinstance(date_val, date):
        return date_val

    s = str(date_val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    if len(s) == 6 and s.isdigit():
        try:
            yy = int(s[:2])
            mm = int(s[2:4])
            dd = int(s[4:6])
            curr_yy = date.today().year % 100
            century = 1900 if yy > curr_yy else 2000
            return date(century + yy, mm, dd)
        except ValueError:
            pass
    return None


def calculate_age(dob: date, reference_date: Optional[date] = None) -> int:
    """Calculates age in full years given date of birth."""
    today = reference_date or date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def validate_demographics(
    date_of_birth: Optional[Union[str, date]] = None,
    expiry_date: Optional[Union[str, date]] = None,
) -> Tuple[bool, List[Dict[str, str]]]:
    """Validates DOB age requirements and document expiration status.

    Returns:
        Tuple of (is_valid: bool, issues: List[Dict[str, str]])
    """
    issues = []
    today = date.today()

    if date_of_birth:
        dob = parse_flexible_date(date_of_birth)
        if dob:
            if dob > today:
                issues.append({
                    "code": "FUTURE_DOB",
                    "field_name": "date_of_birth",
                    "severity": "ERROR",
                    "message": f"Date of birth cannot be in the future ({dob})",
                })
            else:
                age = calculate_age(dob, today)
                if age > 120:
                    issues.append({
                        "code": "INVALID_DOB_RANGE",
                        "field_name": "date_of_birth",
                        "severity": "ERROR",
                        "message": f"Calculated age {age} exceeds reasonable lifetime",
                    })
                elif age < 18:
                    issues.append({
                        "code": "APPLICANT_UNDERAGE",
                        "field_name": "date_of_birth",
                        "severity": "ERROR",
                        "message": f"Applicant must be at least 18 years of age (current age: {age})",
                    })
        else:
            issues.append({
                "code": "INVALID_DOB_FORMAT",
                "field_name": "date_of_birth",
                "severity": "ERROR",
                "message": f"Unable to parse date of birth format '{date_of_birth}'",
            })

    if expiry_date:
        exp = parse_flexible_date(expiry_date)
        if exp:
            if exp < today:
                issues.append({
                    "code": "DOCUMENT_EXPIRED",
                    "field_name": "expiry_date",
                    "severity": "ERROR",
                    "message": f"Document expired on {exp.isoformat()}",
                })
            elif exp <= today + timedelta(days=90):
                issues.append({
                    "code": "DOCUMENT_EXPIRING_SOON",
                    "field_name": "expiry_date",
                    "severity": "WARNING",
                    "message": f"Document expires soon on {exp.isoformat()} (within 90 days)",
                })
            else:
                issues.append({
                    "code": "DOCUMENT_VALID",
                    "field_name": "expiry_date",
                    "severity": "INFO",
                    "message": f"Document is valid until {exp.isoformat()}",
                })
        else:
            issues.append({
                "code": "INVALID_EXPIRY_FORMAT",
                "field_name": "expiry_date",
                "severity": "WARNING",
                "message": f"Unable to parse document expiry date format '{expiry_date}'",
            })

    is_valid = not any(i["severity"] == "ERROR" for i in issues)
    return is_valid, issues
