"""Passport MRZ (ICAO Doc 9303) Validation Engine.

Implements 7-3-1 weighting modulo 10 checksum verification across:
- Document Number check digit
- Date of Birth check digit
- Expiry Date check digit
- Composite check digit
Supports standard ICAO Doc 9303 TD3 format (2 lines of 44 characters)
and standalone Indian passport number regex fallback.
"""
import re
from typing import Dict, List, Optional, Tuple

MRZ_WEIGHTS = [7, 3, 1]
PASSPORT_NUMBER_REGEX = re.compile(r"^[A-PR-WYZ][0-9]{7}$")


def char_value(c: str) -> int:
    """Maps ICAO character to numeric value: 0-9 -> 0-9, A-Z -> 10-35, '<' -> 0."""
    c = c.upper()
    if c.isdigit():
        return int(c)
    elif "A" <= c <= "Z":
        return ord(c) - ord("A") + 10
    elif c == "<":
        return 0
    return 0


def calculate_mrz_check_digit(data_str: str) -> int:
    """Computes ICAO 7-3-1 modulo 10 check digit for a string."""
    total = 0
    for i, c in enumerate(data_str):
        weight = MRZ_WEIGHTS[i % 3]
        total += char_value(c) * weight
    return total % 10


def validate_mrz_checksum(data_str: str, expected_check: str) -> bool:
    """Validates whether data_str computes to expected_check digit."""
    if not expected_check or not expected_check.isdigit():
        return False
    return calculate_mrz_check_digit(data_str) == int(expected_check)


def parse_and_validate_mrz(mrz_text: str) -> Tuple[bool, Dict[str, str], List[Dict[str, str]]]:
    """Parses MRZ lines, extracts fields, and validates check digits.

    Returns:
        (is_valid, extracted_dict, issues)
    """
    issues = []
    extracted: Dict[str, str] = {}

    if not mrz_text:
        issues.append({
            "code": "MRZ_MISSING",
            "field_name": "passport_mrz",
            "severity": "ERROR",
            "message": "Passport MRZ data is missing",
        })
        return False, extracted, issues

    lines = [line.strip().replace(" ", "") for line in mrz_text.strip().splitlines() if line.strip()]

    if len(lines) == 1:
        single = lines[0]
        if len(single) == 88:
            lines = [single[:44], single[44:88]]
        elif len(single) == 8 and PASSPORT_NUMBER_REGEX.match(single):
            extracted["document_number"] = single
            return True, extracted, issues

    if len(lines) < 2:
        issues.append({
            "code": "MRZ_CHECKSUM_MISMATCH",
            "field_name": "passport_mrz",
            "severity": "ERROR",
            "message": "Passport MRZ must contain at least 2 lines of 44 characters (TD3)",
        })
        return False, extracted, issues

    line1 = lines[0].ljust(44, "<")[:44]
    line2 = lines[1].ljust(44, "<")[:44]

    doc_type = line1[0:2].replace("<", "")
    issuing_country = line1[2:5].replace("<", "")
    names_raw = line1[5:44].split("<<")
    surname = names_raw[0].replace("<", " ").strip() if len(names_raw) > 0 else ""
    given_names = names_raw[1].replace("<", " ").strip() if len(names_raw) > 1 else ""
    full_name = f"{given_names} {surname}".strip()

    extracted["document_type"] = doc_type
    extracted["issuing_country"] = issuing_country
    extracted["full_name"] = full_name

    doc_num_str = line2[0:9]
    doc_num_check = line2[9]
    clean_doc_num = doc_num_str.replace("<", "")

    dob_str = line2[13:19]
    dob_check = line2[19]

    expiry_str = line2[21:27]
    expiry_check = line2[27]

    composite_data = line2[0:10] + line2[13:20] + line2[21:43]
    composite_check = line2[43]

    extracted["document_number"] = clean_doc_num
    extracted["date_of_birth_mrz"] = dob_str
    extracted["expiry_date_mrz"] = expiry_str

    if not validate_mrz_checksum(doc_num_str, doc_num_check):
        issues.append({
            "code": "MRZ_CHECKSUM_MISMATCH",
            "field_name": "passport_number",
            "severity": "ERROR",
            "message": f"Passport document number check digit mismatch (computed {calculate_mrz_check_digit(doc_num_str)}, expected {doc_num_check})",
        })

    if not validate_mrz_checksum(dob_str, dob_check):
        issues.append({
            "code": "MRZ_CHECKSUM_MISMATCH",
            "field_name": "date_of_birth",
            "severity": "ERROR",
            "message": f"Passport DOB check digit mismatch (computed {calculate_mrz_check_digit(dob_str)}, expected {dob_check})",
        })

    if not validate_mrz_checksum(expiry_str, expiry_check):
        issues.append({
            "code": "MRZ_CHECKSUM_MISMATCH",
            "field_name": "expiry_date",
            "severity": "ERROR",
            "message": f"Passport expiry date check digit mismatch (computed {calculate_mrz_check_digit(expiry_str)}, expected {expiry_check})",
        })

    if composite_check.isdigit() and not validate_mrz_checksum(composite_data, composite_check):
        issues.append({
            "code": "MRZ_CHECKSUM_MISMATCH",
            "field_name": "passport_mrz",
            "severity": "ERROR",
            "message": "Passport MRZ composite checksum verification failed",
        })

    is_valid = len(issues) == 0
    return is_valid, extracted, issues
