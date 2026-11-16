"""
Synthetic Biometric Fixtures for CKYC / eKYC Testing.

Provides paired in-memory facial images for selfie-to-ID photo matching:
1. Matched facial image pair (high similarity > 0.85, is_match=True).
2. Mismatched facial image pair (low similarity < 0.40, is_match=False).
3. Corrupted / truncated facial image bytes for negative boundary tests.
4. Deterministic pixel histogram / similarity evaluator.
"""

import binascii
import struct
import zlib
from typing import Optional, Tuple


def _build_png_image(pixels_rgb: list, width: int, height: int) -> bytes:
    """Helper to assemble a valid PNG byte stream from RGB pixel list."""
    signature = b"\x89PNG\r\n\x1a\n"

    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_chunk = _png_chunk(b"IHDR", ihdr_data)

    raw_bytes = bytearray()
    for y in range(height):
        raw_bytes.append(0)
        row_pixels = pixels_rgb[y * width : (y + 1) * width]
        for r, g, b in row_pixels:
            raw_bytes.extend([r, g, b])

    compressed = zlib.compress(bytes(raw_bytes))
    idat_chunk = _png_chunk(b"IDAT", compressed)
    iend_chunk = _png_chunk(b"IEND", b"")

    return signature + ihdr_chunk + idat_chunk + iend_chunk


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """Formats a standard PNG chunk with length, type, data, and CRC32."""
    length = struct.pack(">I", len(data))
    type_and_data = chunk_type + data
    crc = struct.pack(">I", binascii.crc32(type_and_data) & 0xFFFFFFFF)
    return length + type_and_data + crc


def _render_synthetic_face(
    skin_color: Tuple[int, int, int] = (235, 195, 160),
    eye_color: Tuple[int, int, int] = (40, 25, 20),
    bg_color: Tuple[int, int, int] = (245, 245, 250),
    perturbation: int = 0
) -> bytes:
    """
    Renders a 32x32 synthetic facial image as valid PNG bytes.
    Features: background, head oval, left eye, right eye, nose, mouth.
    """
    width, height = 32, 32
    pixels = []

    for y in range(height):
        for x in range(width):
            dx = (x - 16) / 10.0
            dy = (y - 16) / 13.0
            dist_sq = dx * dx + dy * dy

            if dist_sq <= 1.0:
                if (y in (11, 12, 13)) and (x in (10, 11, 12) or x in (20, 21, 22)):
                    r, g, b = eye_color
                elif (y in (16, 17)) and (x in (15, 16, 17)):
                    r = max(0, skin_color[0] - 20)
                    g = max(0, skin_color[1] - 20)
                    b = max(0, skin_color[2] - 20)
                elif (y in (22, 23)) and (11 <= x <= 21):
                    r, g, b = (190, 75, 75)
                else:
                    r = min(255, max(0, skin_color[0] + perturbation))
                    g = min(255, max(0, skin_color[1] + perturbation))
                    b = min(255, max(0, skin_color[2] + perturbation))
            else:
                r, g, b = bg_color

            pixels.append((r, g, b))

    return _build_png_image(pixels, width, height)


# ============================================================================
# 1. Matched Facial Pair Generator
# ============================================================================

def generate_matched_facial_pair() -> Tuple[bytes, bytes]:
    """
    Generates a paired (selfie_bytes, id_crop_bytes) representing the SAME subject.
    Similarity > 0.85 in biometric matching.
    """
    subject_skin = (230, 190, 155)
    subject_eye = (35, 20, 15)

    selfie_bytes = _render_synthetic_face(
        skin_color=subject_skin,
        eye_color=subject_eye,
        perturbation=2
    )

    id_crop_bytes = _render_synthetic_face(
        skin_color=subject_skin,
        eye_color=subject_eye,
        perturbation=0
    )

    return selfie_bytes, id_crop_bytes


# ============================================================================
# 2. Mismatched Facial Pair Generator (Impostor Detection)
# ============================================================================

def generate_mismatched_facial_pair() -> Tuple[bytes, bytes]:
    """
    Generates a divergent (selfie_bytes, impostor_id_crop_bytes) representing
    TWO DIFFERENT subjects. Similarity < 0.40, is_match=False.
    """
    selfie_bytes = _render_synthetic_face(
        skin_color=(240, 205, 175),
        eye_color=(30, 20, 10),
        bg_color=(250, 250, 255)
    )

    impostor_bytes = _render_synthetic_face(
        skin_color=(115, 80, 55),
        eye_color=(200, 200, 220),
        bg_color=(30, 35, 45)
    )

    return selfie_bytes, impostor_bytes


# ============================================================================
# 3. Corrupted / Boundary Facial Image Generator
# ============================================================================

def generate_corrupted_facial_image() -> bytes:
    """Generates malformed image bytes to test biometric error handling."""
    return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"CORRUPTED_DATA_TRUNCATED"


# ============================================================================
# 4. Deterministic Similarity Metric Evaluator
# ============================================================================

def _extract_png_pixel_bytes(png_bytes: bytes) -> Optional[bytes]:
    """Helper to extract decompressed scanline pixel bytes from PNG data."""
    if not png_bytes or not png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return None
    try:
        idx = 8
        idat_parts = []
        while idx + 8 <= len(png_bytes):
            chunk_len = struct.unpack(">I", png_bytes[idx:idx+4])[0]
            chunk_type = png_bytes[idx+4:idx+8]
            chunk_data = png_bytes[idx+8:idx+8+chunk_len]
            if chunk_type == b"IDAT":
                idat_parts.append(chunk_data)
            elif chunk_type == b"IEND":
                break
            idx += 12 + chunk_len
        if idat_parts:
            return zlib.decompress(b"".join(idat_parts))
    except Exception:
        return None
    return None


def compute_facial_similarity_metric(image1_bytes: bytes, image2_bytes: bytes) -> float:
    """
    Computes a deterministic normalized similarity score (0.0 to 1.0)
    between two image byte arrays based on pixel divergence and histogram correlation.
    """
    if not image1_bytes or not image2_bytes:
        return 0.0

    raw1 = _extract_png_pixel_bytes(image1_bytes)
    raw2 = _extract_png_pixel_bytes(image2_bytes)

    if raw1 is not None and raw2 is not None:
        min_len = min(len(raw1), len(raw2))
        max_len = max(len(raw1), len(raw2))
        if max_len == 0:
            return 0.0
        mae = sum(abs(raw1[i] - raw2[i]) for i in range(min_len))
        # penalize any remaining trailing length
        mae += (max_len - min_len) * 128
        avg_diff = mae / max_len
        score = max(0.0, min(1.0, 1.0 - (avg_diff / 255.0)))
        return round(float(score), 4)

    # Fallback to byte-level histogram correlation
    hist1 = [0] * 256
    hist2 = [0] * 256

    for b in image1_bytes:
        hist1[b] += 1
    for b in image2_bytes:
        hist2[b] += 1

    len1 = len(image1_bytes)
    len2 = len(image2_bytes)
    norm1 = [h / len1 for h in hist1]
    norm2 = [h / len2 for h in hist2]

    intersection = sum(min(norm1[i], norm2[i]) for i in range(256))
    return round(float(intersection), 4)
