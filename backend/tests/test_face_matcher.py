"""Unit tests for biometric face matcher, byte histogram fallback, and image validation."""
import pytest
from fastapi import HTTPException

from app.services.face_matching.matcher import (
    FaceMatcherEngine,
    FaceMatchResult,
    compute_byte_histogram_similarity,
)


def test_byte_histogram_similarity():
    """Verify byte histogram intersection algorithm."""
    # Identical bytes -> similarity 1.0
    sample_a = b"A" * 100 + b"B" * 100
    assert compute_byte_histogram_similarity(sample_a, sample_a) == 1.0

    # Completely disjoint bytes -> similarity 0.0
    sample_b = b"C" * 200
    assert compute_byte_histogram_similarity(sample_a, sample_b) == 0.0

    # Empty payload
    assert compute_byte_histogram_similarity(b"", sample_a) == 0.0


def test_face_matcher_empty_or_corrupt_payload():
    """Verify validation guards catch empty, short, or corrupted payloads."""
    engine = FaceMatcherEngine()

    # Empty selfie
    with pytest.raises(HTTPException) as exc_info:
        engine.validate_image_payloads(b"", b"valid_image_bytes_exceeding_30_bytes_length")
    assert exc_info.value.status_code == 400
    assert "INVALID_IMAGE_DATA" in exc_info.value.detail

    # Corrupt / truncated marker
    corrupt_selfie = b"Header" + b"CORRUPTED_DATA_TRUNCATED" + b"Padding" * 5
    with pytest.raises(HTTPException) as exc_info:
        engine.validate_image_payloads(corrupt_selfie, b"valid_image_bytes_exceeding_30_bytes_length")
    assert exc_info.value.status_code == 400
    assert "INVALID_IMAGE_DATA" in exc_info.value.detail


def test_face_matcher_multiple_faces_detected():
    """Verify guard flags adversarial multi-face payloads."""
    engine = FaceMatcherEngine()
    multi_face = b"IMAGE_HEADER_" + b"MULTIPLE_FACES" + b"_PAYLOAD_LONG_ENOUGH"
    
    with pytest.raises(HTTPException) as exc_info:
        engine.validate_image_payloads(multi_face, None)
    assert exc_info.value.status_code == 400
    assert "MULTIPLE_FACES_DETECTED" in exc_info.value.detail


def test_face_matcher_compare_faces():
    """Verify compare_faces produces valid FaceMatchResult."""
    engine = FaceMatcherEngine(default_threshold=0.75)
    
    # Valid synthetic bytes
    img1 = b"VALID_IMAGE_DATA_PADDING_TO_OVER_THIRTY_BYTES_A1" * 2
    img2 = b"VALID_IMAGE_DATA_PADDING_TO_OVER_THIRTY_BYTES_A1" * 2
    
    result = engine.compare_faces(img1, img2)
    assert isinstance(result, FaceMatchResult)
    assert result.confidence >= 0.0
    assert isinstance(result.is_match, bool)
    assert result.method in ("opencv_hsv_correlation", "histogram_correlation")
