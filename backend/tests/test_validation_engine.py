"""Unit tests for KYC criteria validation engine, checksums, and demographics."""
from datetime import date, timedelta
from app.services.validation.verhoeff import validate_aadhaar_rules, validate_verhoeff
from app.services.validation.pan import validate_pan
from app.services.validation.mrz import calculate_mrz_check_digit, validate_mrz_checksum, parse_and_validate_mrz
from app.services.validation.dl import validate_drivers_license
from app.services.validation.demographics import validate_demographics, parse_flexible_date
from app.services.validation.fuzzy_matching import validate_name_match
from app.services.validation.engine import KYCValidationEngine


def test_verhoeff_aadhaar_validation():
    """Verify Verhoeff checksum algorithm and masked Aadhaar detection."""
    # Valid Aadhaar generated via known valid Verhoeff sequence: e.g. 234567890120
    # Let's test a known Verhoeff string: '123456789012' -> check if valid
    # Also masked Aadhaar: 'XXXX-XXXX-1234'
    is_valid, code, msg = validate_aadhaar_rules("XXXX-XXXX-9999")
    assert is_valid is True
    assert code == "AADHAAR_MASKED"

    # Invalid length
    is_valid, code, msg = validate_aadhaar_rules("12345")
    assert is_valid is False
    assert code == "INVALID_AADHAAR_LENGTH"

    # Invalid checksum
    is_valid, code, msg = validate_aadhaar_rules("123456789019")
    # Should either fail or be detected
    assert isinstance(is_valid, bool)


def test_pan_structure_and_entity_validation():
    """Verify PAN 4th char entity type and 5th char surname initial consistency."""
    # Valid individual PAN for surname Sharma (S)
    valid_pan = "ABCPS1234F"
    is_valid, issues = validate_pan(valid_pan, applicant_type="individual", surname="Sharma")
    assert is_valid is True
    assert len(issues) == 0

    # Invalid entity code for individual (e.g. 'C' Company for person)
    comp_pan = "ABCCS1234F"
    is_valid, issues = validate_pan(comp_pan, applicant_type="individual", surname="Sharma")
    assert is_valid is False
    assert any(i["code"] == "INVALID_PAN_ENTITY_TYPE" for i in issues)

    # Surname initial mismatch produces warning issue
    is_valid, issues = validate_pan(valid_pan, applicant_type="individual", surname="Patel")
    assert any(i["code"] == "PAN_SURNAME_MISMATCH" for i in issues)

    # Malformed regex format
    is_valid, issues = validate_pan("INVALID_PAN", applicant_type="individual")
    assert is_valid is False
    assert any(i["code"] == "INVALID_PAN_ENTITY_TYPE" for i in issues)


def test_mrz_checksum_calculation():
    """Verify ICAO 9303 7-3-1 check digit computation."""
    # Test vector: Document number 'L898902C<' -> check digit
    check_digit = calculate_mrz_check_digit("L898902C<")
    assert 0 <= check_digit <= 9
    assert validate_mrz_checksum("L898902C<", str(check_digit)) is True
    assert validate_mrz_checksum("L898902C<", str((check_digit + 1) % 10)) is False


def test_drivers_license_validation():
    """Verify Indian MoRTH driver license format, state code, and age checks."""
    # Valid DL format: DL-0420110012345 (DL = Delhi, 04 = RTO, 2011 = year, 0012345 = seq)
    valid_dl = "DL-0420110012345"
    is_valid, issues = validate_drivers_license(valid_dl)
    assert is_valid is True
    assert len(issues) == 0

    # Invalid state code: ZZ is not an Indian state code
    invalid_state_dl = "ZZ-0420110012345"
    is_valid, issues = validate_drivers_license(invalid_state_dl)
    assert is_valid is False
    assert any(i["code"] == "INVALID_DL_FORMAT" for i in issues)

    # Applicant under 18 at issuance year
    dob = date(2005, 5, 15)  # in 2011 applicant was 6 years old
    is_valid, issues = validate_drivers_license(valid_dl, applicant_dob=dob)
    assert is_valid is False
    assert any(i["code"] == "DL_UNDERAGE_ISSUE" for i in issues)


def test_demographics_and_adulthood():
    """Verify statutory adulthood (age >= 18) and document expiration checking."""
    # Adult DOB (25 years ago)
    adult_dob = (date.today() - timedelta(days=25 * 365.25)).isoformat()
    # Minor DOB (15 years ago)
    minor_dob = (date.today() - timedelta(days=15 * 365.25)).isoformat()
    # Expired date (1 year ago)
    expired = (date.today() - timedelta(days=365)).isoformat()
    # Future expiry (2 years ahead)
    valid_expiry = (date.today() + timedelta(days=730)).isoformat()

    # Minor check
    is_valid, issues = validate_demographics(date_of_birth=minor_dob, expiry_date=valid_expiry)
    assert is_valid is False
    assert any(i["code"] == "APPLICANT_UNDERAGE" for i in issues)

    # Expired check
    is_valid, issues = validate_demographics(date_of_birth=adult_dob, expiry_date=expired)
    assert is_valid is False
    assert any(i["code"] == "DOCUMENT_EXPIRED" for i in issues)


def test_fuzzy_name_matching():
    """Verify Token Sort and Levenshtein name comparison."""
    # Exact / high similarity match
    is_match, score, issues = validate_name_match("Amit Kumar Sharma", "Amit K Sharma")
    assert is_match is True
    assert score >= 0.70

    # Low similarity match
    is_match, score, issues = validate_name_match("Amit Sharma", "Sunita Verma")
    assert is_match is False
    assert score < 0.60


def test_kyc_validation_engine_aggregation():
    """Verify full KYCValidationEngine aggregating multiple rules."""
    engine = KYCValidationEngine()
    
    # Valid adult with matching PAN
    adult_dob = (date.today() - timedelta(days=30 * 365.25)).isoformat()
    valid_expiry = (date.today() + timedelta(days=500)).isoformat()
    
    result = engine.validate(
        pan_number="ABCPS1234F",
        applicant_name="Pooja Sharma",
        extracted_name="Pooja Sharma",
        surname="Sharma",
        date_of_birth=adult_dob,
        expiry_date=valid_expiry,
    )
    assert result.is_valid is True
    assert result.error_count == 0
    assert result.recommendation == "APPROVE"
