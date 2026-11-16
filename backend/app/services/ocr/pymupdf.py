"""Tier 1 PyMuPDF Digital PDF Text Stream Extractor."""
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    fitz = None
    PYMUPDF_AVAILABLE = False


def extract_text_from_pdf_stream(file_bytes: bytes) -> Optional[List[Tuple[int, str]]]:
    """Extracts digital text page-by-page from in-memory PDF stream using PyMuPDF.

    Returns:
        List of (page_number, text) tuples, or None if extraction is unavailable/empty.
    """
    if not PYMUPDF_AVAILABLE or not file_bytes:
        return None

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages_text: List[Tuple[int, str]] = []
        total_len = 0

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_text = page.get_text()
            pages_text.append((page_idx + 1, page_text))
            total_len += len(page_text.strip())

        doc.close()

        if total_len >= 15:
            return pages_text
        return None
    except Exception as e:
        logger.warning("PyMuPDF digital extraction failed, will fall back: %s", e)
        return None
