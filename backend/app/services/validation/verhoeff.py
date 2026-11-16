"""Verhoeff Algorithm for Aadhaar (12-Digit Indian National ID) & Masked Aadhaar.

Operates on the dihedral group D5 (order 10) to detect 100% of single-digit errors
and 100% of adjacent transposition errors.
"""
import re
from typing import Optional, Tuple

# Multiplication table d(j, k) for D5 dihedral group
VERHOEFF_D = [
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

# Permutation table p(i, j)
VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

# Inverse table inv(j)
VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

MASKED_AADHAAR_REGEX = re.compile(r"^(?:[X*]{4}[-\s]?[X*]{4}[-\s]?([0-9]{4})|[X*]{8}([0-9]{4}))$", re.IGNORECASE)


def compute_verhoeff_checksum(num_str: str) -> int:
    """Computes the Verhoeff check digit for a given numeric string."""
    clean = "".join(c for c in str(num_str) if c.isdigit())
    if not clean:
        return 0
    c = 0
    for i, digit in enumerate(reversed(clean)):
        c = VERHOEFF_D[c][VERHOEFF_P[(i + 1) % 8][int(digit)]]
    return VERHOEFF_INV[c]


def is_masked_aadhaar(num_str: str) -> bool:
    """Checks if the string matches UIDAI masked Aadhaar format (e.g. XXXX-XXXX-1234)."""
    s = str(num_str).strip()
    return bool(MASKED_AADHAAR_REGEX.match(s))


def validate_verhoeff(num_str: str) -> bool:
    """Validates an n-digit string using the Verhoeff D5 dihedral algorithm.

    Returns True if checksum verifies to 0, False otherwise.
    Also returns True for compliant masked Aadhaar strings.
    """
    s = str(num_str).strip()
    if is_masked_aadhaar(s):
        return True

    clean = "".join(c for c in s if c.isdigit())
    if len(clean) != 12:
        return False

    c = 0
    for i, digit in enumerate(reversed(clean)):
        c = VERHOEFF_D[c][VERHOEFF_P[i % 8][int(digit)]]
    return c == 0


def validate_aadhaar_rules(num_str: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Comprehensive Aadhaar format and Verhoeff validation.

    Returns:
        (is_valid, issue_code, issue_message)
    """
    if not num_str:
        return False, "AADHAAR_MISSING", "Aadhaar number is missing"

    s = str(num_str).strip()

    # Check for masked Aadhaar
    if is_masked_aadhaar(s):
        return True, "AADHAAR_MASKED", "Masked Aadhaar format detected (UIDAI compliant). Checksum check bypassed."

    clean = "".join(c for c in s if c.isdigit())
    if len(clean) != 12:
        return False, "INVALID_AADHAAR_LENGTH", f"Aadhaar number must contain exactly 12 digits, found {len(clean)}"

    # First digit cannot be 0 or 1
    if clean[0] in ("0", "1"):
        return False, "AADHAAR_INVALID_STARTING_DIGIT", f"Aadhaar number cannot begin with {clean[0]} (must be 2-9)"

    if not validate_verhoeff(clean):
        return False, "INVALID_VERHOEFF_CHECKSUM", "Aadhaar number failed Verhoeff dihedral D5 checksum verification"

    return True, None, None
