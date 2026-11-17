"""
Synthetic Data Fixtures for CKYC / eKYC Testing.

Provides mathematically and algorithmically accurate generators and validators:
1. Verhoeff algorithm for 12-digit Aadhaar (D5 dihedral group multiplication, permutation, and inverse tables).
2. PAN generator and validator adhering to Indian Income Tax Department rules.
3. Passport MRZ generator and validator (ICAO Doc 9303 Type 3 / TD3 format, 2 lines x 44 chars, 7-3-1 modulo 10 checksums).
4. Driving Licence (DL) generator and validator (standard Indian MoRTH format).
5. Demographic profiles generator (adult applicant >= 18, minor applicant < 18, corporate entity).
"""

import random
import re
import string
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# ============================================================================
# 1. Verhoeff Algorithm Implementation (Dihedral Group D5)
# ============================================================================

# Multiplication table for Dihedral group D5
VERHOEFF_D: List[List[int]] = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

# Permutation table P (8 permutations for position mod 8)
VERHOEFF_P: List[List[int]] = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

# Inverse table Inv
VERHOEFF_INV: List[int] = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def compute_verhoeff_checksum(number_str: str) -> int:
    """
    Computes the Verhoeff check digit for a given numeric string.
    The check digit is the single digit (0-9) that when appended to number_str
    satisfies validate_verhoeff(number_str + check_digit) == True.
    """
    clean_str = "".join(c for c in str(number_str) if c.isdigit())
    if not clean_str:
        raise ValueError("Cannot compute Verhoeff checksum on empty numeric string")

    c = 0
    for i, char in enumerate(reversed(clean_str)):
        c = VERHOEFF_D[c][VERHOEFF_P[(i + 1) % 8][int(char)]]
    return VERHOEFF_INV[c]


def validate_verhoeff(number_str: str) -> bool:
    """
    Validates a number with its Verhoeff check digit included at the end.
    Returns True if valid, False otherwise.
    """
    clean_str = "".join(c for c in str(number_str) if c.isdigit())
    if not clean_str or len(clean_str) < 2:
        return False

    c = 0
    for i, char in enumerate(reversed(clean_str)):
        c = VERHOEFF_D[c][VERHOEFF_P[i % 8][int(char)]]
    return c == 0


def generate_valid_aadhaar() -> str:
    """
    Generates a valid 12-digit Aadhaar number with correct Verhoeff check digit.
    UIDAI rule: Aadhaar numbers start with digits 2-9 (not 0 or 1).
    """
    first_digit = str(random.randint(2, 9))
    middle_10_digits = "".join(str(random.randint(0, 9)) for _ in range(10))
    first_11 = first_digit + middle_10_digits
    check_digit = compute_verhoeff_checksum(first_11)
    aadhaar = first_11 + str(check_digit)
    assert validate_verhoeff(aadhaar), "Generated Aadhaar must be valid"
    return aadhaar


def generate_invalid_aadhaar() -> str:
    """
    Generates an invalid 12-digit Aadhaar number guaranteed to fail Verhoeff check.
    Uses check digit corruption.
    """
    valid = generate_valid_aadhaar()
    digits = list(valid)
    curr_check = int(digits[-1])
    digits[-1] = str((curr_check + random.randint(1, 9)) % 10)
    invalid = "".join(digits)
    if validate_verhoeff(invalid):
        digits[-1] = str((int(digits[-1]) + 1) % 10)
        invalid = "".join(digits)
    return invalid


# ============================================================================
# 2. PAN Generator and Validator (Income Tax Department Rules)
# ============================================================================

PAN_ENTITY_TYPES = ["P", "C", "H", "F", "A", "T", "B", "L", "J", "G"]
PAN_REGEX = re.compile(r"^[A-Z]{3}[ABCFGHLJPT][A-Z][0-9]{4}[A-Z]$")


def validate_pan(pan: str) -> bool:
    """
    Validates a Permanent Account Number (PAN) according to Income Tax rules.
    10 characters: [A-Z]{3} + Entity type + Surname initial + 4 digits + 1 letter.
    """
    if not isinstance(pan, str) or len(pan) != 10:
        return False
    return bool(PAN_REGEX.match(pan.upper()))


def generate_valid_pan(entity_type: str = "P", surname: str = "SHARMA") -> str:
    """
    Generates a valid 10-character PAN string.
    - Chars 1-3: Random uppercase letters
    - Char 4: Entity type ('P' for Individual, 'C' for Company, etc.)
    - Char 5: Surname initial (or first letter of corporate name)
    - Chars 6-9: 4 digits (0001 - 9999)
    - Char 10: Check letter (A-Z)
    """
    entity = entity_type.upper() if entity_type.upper() in PAN_ENTITY_TYPES else "P"
    clean_surname = re.sub(r"[^A-Za-z]", "", surname)
    fifth_char = clean_surname[0].upper() if clean_surname else "S"

    first_three = "".join(random.choices(string.ascii_uppercase, k=3))
    digits = f"{random.randint(1000, 9999):04d}"
    last_char = random.choice(string.ascii_uppercase)

    pan = f"{first_three}{entity}{fifth_char}{digits}{last_char}"
    assert validate_pan(pan), f"Generated PAN {pan} must be valid"
    return pan


def generate_invalid_pan(reason: str = "entity") -> str:
    """
    Generates an invalid PAN based on specified violation type:
    - 'entity': invalid 4th character (not in PAN_ENTITY_TYPES)
    - 'length': invalid length (!= 10)
    - 'digits': letters where digits are expected
    - 'format': invalid prefix or suffix characters
    """
    if reason == "entity":
        first_three = "".join(random.choices(string.ascii_uppercase, k=3))
        invalid_entity = "X"
        digits = f"{random.randint(1000, 9999):04d}"
        last_char = random.choice(string.ascii_uppercase)
        return f"{first_three}{invalid_entity}S{digits}{last_char}"
    elif reason == "length":
        return "ABCDE1234"  # 9 chars
    elif reason == "digits":
        return "ABCPS123AZ"  # Letter in digit position
    else:
        return "12345ABCDE"  # Completely wrong format


# ============================================================================
# 3. Passport MRZ Generator and Validator (ICAO Doc 9303 TD3 Format)
# ============================================================================

MRZ_WEIGHTS = [7, 3, 1]


def compute_mrz_check_digit(data_str: str) -> str:
    """
    Computes single check digit (0-9) according to ICAO Doc 9303 Part 4.
    Weights cycle 7, 3, 1.
    """
    total = 0
    for idx, char in enumerate(data_str.upper()):
        weight = MRZ_WEIGHTS[idx % 3]
        if char.isdigit():
            val = int(char)
        elif "A" <= char <= "Z":
            val = ord(char) - 55  # 'A' is 65 -> 10
        elif char == "<":
            val = 0
        else:
            val = 0
        total += val * weight
    return str(total % 10)


def validate_mrz_check_digit(data_str: str, check_digit: str) -> bool:
    """Validates an MRZ segment against its trailing check digit."""
    if not check_digit or not check_digit.isdigit():
        return False
    return compute_mrz_check_digit(data_str) == check_digit


def generate_valid_passport_mrz(
    doc_number: str = "J84920184",
    country_code: str = "IND",
    surname: str = "SHARMA",
    given_names: str = "AARAV",
    nationality: str = "IND",
    dob: str = "900515",  # YYMMDD
    sex: str = "M",
    expiry_date: str = "300101",
    personal_number: str = "294828472841"
) -> str:
    """
    Generates a valid 2-line x 44-character TD3 Machine Readable Zone (MRZ).
    """
    clean_surname = re.sub(r"[^A-Z]", "", surname.upper())
    clean_given = re.sub(r"[^A-Z]", "<", given_names.upper())
    name_field = f"{clean_surname}<<{clean_given}"
    if len(name_field) > 39:
        name_field = name_field[:39]
    else:
        name_field = name_field.ljust(39, "<")
    line1 = f"P<{country_code.upper()[:3]}{name_field}"
    assert len(line1) == 44, f"Line 1 length must be 44, got {len(line1)}"

    clean_doc = re.sub(r"[^A-Z0-9]", "", doc_number.upper()).ljust(9, "<")[:9]
    doc_check = compute_mrz_check_digit(clean_doc)

    nat = country_code.upper()[:3]
    dob_clean = re.sub(r"[^0-9]", "", dob)[:6].ljust(6, "0")
    dob_check = compute_mrz_check_digit(dob_clean)

    sex_char = sex.upper()[0] if sex and sex.upper()[0] in ["M", "F"] else "<"

    exp_clean = re.sub(r"[^0-9]", "", expiry_date)[:6].ljust(6, "0")
    exp_check = compute_mrz_check_digit(exp_clean)

    clean_pers = re.sub(r"[^A-Z0-9]", "", personal_number.upper()).ljust(14, "<")[:14]
    pers_check = compute_mrz_check_digit(clean_pers) if any(c != "<" for c in clean_pers) else "<"

    composite_data = (
        clean_doc + doc_check +
        dob_clean + dob_check +
        exp_clean + exp_check + clean_pers + pers_check
    )
    composite_check = compute_mrz_check_digit(composite_data)

    line2 = (
        f"{clean_doc}{doc_check}{nat}{dob_clean}{dob_check}{sex_char}"
        f"{exp_clean}{exp_check}{clean_pers}{pers_check}{composite_check}"
    )
    assert len(line2) == 44, f"Line 2 length must be 44, got {len(line2)}"

    return f"{line1}\n{line2}"


def validate_passport_mrz(mrz_str: str) -> Dict[str, Any]:
    """
    Validates a 2-line TD3 passport MRZ string.
    """
    lines = [line.strip() for line in mrz_str.strip().splitlines() if line.strip()]
    if len(lines) != 2:
        return {"is_valid": False, "error": f"Expected 2 lines, got {len(lines)}"}

    line1, line2 = lines[0], lines[1]
    if len(line1) != 44 or len(line2) != 44:
        return {
            "is_valid": False,
            "error": f"Invalid line lengths: line1={len(line1)}, line2={len(line2)} (must be 44)"
        }

    doc_num = line2[0:9]
    doc_check = line2[9]
    dob = line2[13:19]
    dob_check = line2[19]
    exp = line2[21:27]
    exp_check = line2[27]
    pers = line2[28:42]
    pers_check = line2[42]
    composite_check = line2[43]

    doc_valid = validate_mrz_check_digit(doc_num, doc_check)
    dob_valid = validate_mrz_check_digit(dob, dob_check)
    exp_valid = validate_mrz_check_digit(exp, exp_check)

    pers_valid = True
    if pers_check != "<":
        pers_valid = validate_mrz_check_digit(pers, pers_check)

    composite_data = (
        doc_num + doc_check +
        dob + dob_check +
        exp + exp_check + pers + pers_check
    )
    composite_valid = (compute_mrz_check_digit(composite_data) == composite_check)

    is_valid = all([doc_valid, dob_valid, exp_valid, pers_valid, composite_valid])
    return {
        "is_valid": is_valid,
        "doc_check_valid": doc_valid,
        "dob_check_valid": dob_valid,
        "exp_check_valid": exp_valid,
        "pers_check_valid": pers_valid,
        "composite_check_valid": composite_valid,
        "document_number": doc_num.replace("<", ""),
        "date_of_birth": dob,
        "expiry_date": exp,
    }


def generate_invalid_passport_mrz(reason: str = "checksum") -> str:
    """Generates an invalid Passport MRZ."""
    valid_mrz = generate_valid_passport_mrz()
    lines = valid_mrz.splitlines()
    line1, line2 = lines[0], lines[1]

    if reason == "checksum":
        orig_check = line2[9]
        corrupted = str((int(orig_check) + 1) % 10) if orig_check.isdigit() else "9"
        line2 = line2[:9] + corrupted + line2[10:]
    elif reason == "length":
        line2 = line2[:40]
    else:
        orig_comp = line2[43]
        corrupted = str((int(orig_comp) + 1) % 10) if orig_comp.isdigit() else "9"
        line2 = line2[:43] + corrupted

    return f"{line1}\n{line2}"


# ============================================================================
# 4. Driving Licence (DL) Generator and Validator
# ============================================================================

INDIAN_STATE_CODES = [
    "DL", "MH", "KA", "TN", "UP", "GJ", "RJ", "WB", "TS", "AP",
    "KL", "HR", "PB", "MP", "BR", "OR", "AS", "JH", "CH", "UT"
]

DL_REGEX = re.compile(r"^([A-Z]{2})([0-9]{2})([0-9]{4})([0-9]{7})$")


def validate_dl(dl_number: str) -> bool:
    """Validates an Indian Driving Licence number."""
    clean_dl = re.sub(r"[\s\-]", "", str(dl_number).upper())
    match = DL_REGEX.match(clean_dl)
    if not match:
        return False
    state, rto, year, serial = match.groups()
    if state not in INDIAN_STATE_CODES:
        return False
    year_int = int(year)
    current_year = date.today().year
    if year_int < 1960 or year_int > current_year:
        return False
    return True


def generate_valid_dl(
    state_code: Optional[str] = None,
    rto: Optional[str] = None,
    year: Optional[int] = None
) -> str:
    """Generates a valid 15-character Indian Driving Licence number."""
    state = state_code.upper() if state_code and state_code.upper() in INDIAN_STATE_CODES else random.choice(INDIAN_STATE_CODES)
    rto_code = f"{int(rto):02d}" if rto and str(rto).isdigit() else f"{random.randint(1, 25):02d}"
    issue_year = year if year and 1980 <= year <= date.today().year else random.randint(2015, date.today().year)
    serial_no = f"{random.randint(1, 9999999):07d}"

    dl = f"{state}{rto_code}{issue_year}{serial_no}"
    assert validate_dl(dl), f"Generated DL {dl} must be valid"
    return dl


def generate_invalid_dl(reason: str = "state") -> str:
    """Generates an invalid DL number."""
    if reason == "state":
        return f"XX042021{random.randint(1, 9999999):07d}"
    elif reason == "year":
        return f"DL041850{random.randint(1, 9999999):07d}"
    else:
        return "DL042021"


# ============================================================================
# 5. Demographic Profiles Generator
# ============================================================================

def generate_adult_applicant(
    first_name: str = "Aarav",
    last_name: str = "Sharma",
    min_age: int = 18,
    max_age: int = 65
) -> Dict[str, Any]:
    """Generates an adult applicant profile (age >= 18)."""
    today = date.today()
    age_years = random.randint(min_age, max_age)
    days_offset = random.randint(0, 364)
    birth_date = today - timedelta(days=(age_years * 365 + days_offset))
    dob_str = birth_date.strftime("%Y-%m-%d")

    pan = generate_valid_pan(entity_type="P", surname=last_name)
    aadhaar = generate_valid_aadhaar()
    dl = generate_valid_dl()

    mrz_dob = birth_date.strftime("%y%m%d")
    mrz = generate_valid_passport_mrz(
        surname=last_name,
        given_names=first_name,
        dob=mrz_dob,
        sex="M",
        nationality="IND"
    )

    return {
        "applicant_type": "individual",
        "first_name": first_name,
        "last_name": last_name,
        "full_name": f"{first_name} {last_name}",
        "date_of_birth": dob_str,
        "age": age_years,
        "is_adult": True,
        "is_minor": False,
        "nationality": "IND",
        "email": f"{first_name.lower()}.{last_name.lower()}@example.com",
        "phone": f"+9198{random.randint(10000000, 99999999)}",
        "aadhaar_number": aadhaar,
        "pan_number": pan,
        "dl_number": dl,
        "passport_mrz": mrz,
    }


def generate_minor_applicant(
    first_name: str = "Rohan",
    last_name: str = "Gupta",
    age: int = 15
) -> Dict[str, Any]:
    """Generates a minor applicant profile (age < 18)."""
    today = date.today()
    actual_age = min(age, 17)
    days_offset = random.randint(0, 364)
    birth_date = today - timedelta(days=(actual_age * 365 + days_offset))
    dob_str = birth_date.strftime("%Y-%m-%d")

    pan = generate_valid_pan(entity_type="P", surname=last_name)
    aadhaar = generate_valid_aadhaar()

    return {
        "applicant_type": "individual",
        "first_name": first_name,
        "last_name": last_name,
        "full_name": f"{first_name} {last_name}",
        "date_of_birth": dob_str,
        "age": actual_age,
        "is_adult": False,
        "is_minor": True,
        "nationality": "IND",
        "email": f"{first_name.lower()}.{last_name.lower()}@example.com",
        "phone": f"+9197{random.randint(10000000, 99999999)}",
        "aadhaar_number": aadhaar,
        "pan_number": pan,
    }


def generate_corporate_entity(
    company_name: str = "Apex Logistics Pvt Ltd",
    rep_first_name: str = "Vikram",
    rep_last_name: str = "Malhotra"
) -> Dict[str, Any]:
    """Generates a corporate entity profile."""
    inc_year = random.randint(2010, 2022)
    cin = f"U74999DL{inc_year}PTC{random.randint(100000, 999999)}"
    inc_date = f"{inc_year}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"

    first_char_name = re.sub(r"[^A-Za-z]", "", company_name)[0]
    pan = generate_valid_pan(entity_type="C", surname=first_char_name)

    rep = generate_adult_applicant(first_name=rep_first_name, last_name=rep_last_name)

    return {
        "applicant_type": "business",
        "business_name": company_name,
        "registration_number": cin,
        "cin": cin,
        "incorporation_date": inc_date,
        "pan_number": pan,
        "email": "compliance@apexlogistics.example.com",
        "phone": "+911145678900",
        "representative": {
            "first_name": rep["first_name"],
            "last_name": rep["last_name"],
            "full_name": rep["full_name"],
            "role_title": "Managing Director",
            "email": rep["email"],
            "phone": rep["phone"],
            "pan_number": rep["pan_number"],
            "aadhaar_number": rep["aadhaar_number"],
        }
    }
