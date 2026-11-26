
from pypdf import PdfReader

from analyzer.section_detector import extract_sections
from analyzer.resume_extractor import extract_pdf_text as _extract_pdf_text
from analyzer.ocr import OCRError


def extract_pdf_text(filepath, **kwargs):
    """Extract PDF text while preserving the legacy patchable reader."""
    return _extract_pdf_text(filepath, reader_class=PdfReader, **kwargs)


def extract_pdf_sections(filepath):
    """Extract text from a PDF and return organized resume sections."""
    text = extract_pdf_text(filepath)
    return extract_sections(text)
