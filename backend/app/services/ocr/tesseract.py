"""Tier 2 Tesseract OCR Engine Wrapper with System Availability Check."""
import io
import logging
import shutil
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = bool(shutil.which("tesseract")) or hasattr(pytesseract, "image_to_string")
except ImportError:
    pytesseract = None
    Image = None
    TESSERACT_AVAILABLE = False


def extract_text_via_tesseract(image_bytes: bytes) -> Optional[str]:
    """Runs pytesseract OCR on image bytes if Tesseract binary and PIL are available."""
    if not TESSERACT_AVAILABLE or not image_bytes or pytesseract is None or Image is None:
        return None

    try:
        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img)
        if text and len(text.strip()) > 5:
            return text.strip()
        return None
    except Exception as e:
        logger.warning("Tesseract OCR execution failed, falling back: %s", e)
        return None
