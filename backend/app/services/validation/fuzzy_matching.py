"""Pure-Python Fuzzy Name Matching Engine.

Computes Levenshtein edit distance and Token Sort similarity between applicant name
and OCR-extracted name without external native C dependencies.
"""
import re
from typing import Dict, List, Optional, Tuple

HONORIFICS = {
    "MR", "MRS", "MS", "DR", "SHRI", "SMT", "PROF", "MD", "KUMAR", "KUMARI"
}


def normalize_name(name_str: str) -> str:
    """Normalizes name by uppercase conversion, stripping punctuation, removing honorifics."""
    if not name_str:
        return ""
    s = str(name_str).upper()
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    tokens = [t for t in s.split() if t]
    if len(tokens) > 1:
        filtered = [t for t in tokens if t not in HONORIFICS]
        if filtered:
            tokens = filtered
    return " ".join(tokens)


def levenshtein_distance(s1: str, s2: str) -> int:
    """Computes Levenshtein edit distance between two strings in pure Python."""
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def levenshtein_ratio(s1: str, s2: str) -> float:
    """Computes normalized Levenshtein similarity ratio between 0.0 and 1.0."""
    if not s1 and not s2:
        return 1.0
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    dist = levenshtein_distance(s1, s2)
    return max(0.0, 1.0 - (dist / max_len))


def token_sort_ratio(s1: str, s2: str) -> float:
    """Tokenizes, sorts words alphabetically, and computes Levenshtein ratio."""
    tokens1 = sorted(s1.split())
    tokens2 = sorted(s2.split())
    sorted_s1 = " ".join(tokens1)
    sorted_s2 = " ".join(tokens2)
    return levenshtein_ratio(sorted_s1, sorted_s2)


def compute_name_similarity(name1: str, name2: str) -> float:
    """Computes overall name similarity score (max of direct Levenshtein and Token Sort)."""
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)
    if not norm1 or not norm2:
        return 0.0
    if norm1 == norm2:
        return 1.0
    direct = levenshtein_ratio(norm1, norm2)
    token_sorted = token_sort_ratio(norm1, norm2)
    return round(float(max(direct, token_sorted)), 4)


def validate_name_match(
    applicant_name: Optional[str],
    extracted_name: Optional[str],
    threshold: float = 0.85,
) -> Tuple[bool, float, List[Dict[str, str]]]:
    """Validates whether applicant name matches extracted OCR name.

    Returns:
        Tuple of (is_match: bool, similarity: float, issues: List[Dict[str, str]])
    """
    issues = []
    if not applicant_name or not extracted_name:
        return True, 1.0, issues

    sim = compute_name_similarity(applicant_name, extracted_name)

    if sim >= threshold:
        return True, sim, issues

    if sim >= 0.50:
        issues.append({
            "code": "NAME_SIMILARITY_LOW",
            "field_name": "applicant_name",
            "severity": "WARNING",
            "message": f"Extracted name '{extracted_name}' differs slightly from applicant name '{applicant_name}' (similarity: {sim:.2f})",
        })
        return True, sim, issues
    else:
        issues.append({
            "code": "NAME_MISMATCH",
            "field_name": "applicant_name",
            "severity": "ERROR",
            "message": f"Extracted name '{extracted_name}' does not match applicant profile '{applicant_name}' (similarity: {sim:.2f})",
        })
        return False, sim, issues
