"""Multi-Tier OCR Extraction Engine Manager.

Orchestrates 4-tier waterfall:
- Tier 1: PyMuPDF digital text stream
- Tier 2: pytesseract OCR image fallback
- Tier 3: OpenRouter Vision multimodal API
- Tier 4: Deterministic regex and fixture extractor (100% offline)
"""
import logging
from typing import List, Optional

from app.services.ocr.pymupdf import extract_text_from_pdf_stream
from app.services.ocr.regex_fixture import ExtractedFieldDTO, OCRResult, extract_regex_fields
from app.services.ocr.tesseract import extract_text_via_tesseract
from app.services.ocr.vision import extract_via_openrouter_vision

logger = logging.getLogger(__name__)


class MultiTierOCREngine:
    async def extract_fields(
        self,
        document_type: str,
        file_bytes: Optional[bytes] = None,
        document_text: Optional[str] = None,
    ) -> OCRResult:
        """Executes multi-tier waterfall extraction.

        If document_text is provided directly, runs deterministic regex heuristics.
        If file_bytes is provided, attempts Tier 1 -> Tier 2 -> Tier 3 -> Tier 4.
        """
        if document_text is not None:
            return extract_regex_fields(document_type, document_text)

        if not file_bytes:
            return OCRResult(count=0, fallback_applied=False, extracted_fields=[])

        # Tier 1: PyMuPDF Digital PDF Text
        pdf_pages = extract_text_from_pdf_stream(file_bytes)
        if pdf_pages:
            combined_text = "\n".join(f"--- PAGE {p_num} ---\n{text}" for p_num, text in pdf_pages)
            res = extract_regex_fields(document_type, combined_text)
            if res.count > 0:
                res.fallback_applied = False
                return res

        # Tier 2: Tesseract OCR Image Fallback
        tess_text = extract_text_via_tesseract(file_bytes)
        if tess_text:
            res = extract_regex_fields(document_type, tess_text)
            if res.count > 0:
                return res

        # Tier 3: OpenRouter Vision API (if configured)
        vision_text = await extract_via_openrouter_vision(file_bytes)
        if vision_text:
            res = extract_regex_fields(document_type, vision_text)
            if res.count > 0:
                return res

        # Tier 4: Deterministic Fallback on raw bytes decoded as UTF-8 / ASCII
        try:
            raw_decoded = file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            raw_decoded = ""

        res = extract_regex_fields(document_type, raw_decoded)
        res.fallback_applied = True
        return res


ocr_engine = MultiTierOCREngine()
