"""OCR extraction module for scanned PDF resume pages.

Detects when a PDF page has insufficient extractable text, extracts images
from the page, and uses Tesseract OCR (via pytesseract) to extract readable text.
Provides clear and understandable error handling for OCR failures.
"""

import io
import os
import shutil
from typing import Any, List, Optional
from PIL import Image

try:
    import pytesseract
except ImportError:
    pytesseract = None


class OCRError(Exception):
    """Raised when OCR processing fails. The message is safe and understandable to show to the user."""


def is_tesseract_available() -> bool:
    """Check if Tesseract binary is available on the system PATH or default locations."""
    if pytesseract is None:
        return False

    cmd = getattr(pytesseract.pytesseract, "tesseract_cmd", "tesseract")
    if shutil.which(cmd) or (os.path.isabs(cmd) and os.path.isfile(cmd)):
        return True

    # Check common default locations on Windows
    fallbacks = [
        os.environ.get("TESSERACT_CMD"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    for fallback in fallbacks:
        if fallback and os.path.isfile(fallback):
            pytesseract.pytesseract.tesseract_cmd = fallback
            return True

    return False


def extract_text_from_image(image: Any) -> str:
    """Run OCR on a PIL Image object or image bytes.

    Raises:
        OCRError: If pytesseract is missing, tesseract binary is not found,
                  or tesseract execution fails.
    """
    if pytesseract is None:
        raise OCRError(
            "OCR processing failed: pytesseract is not installed. "
            "Please install pytesseract and Tesseract-OCR to analyze scanned PDF resumes."
        )

    # Ensure tesseract binary path is configured if in standard locations
    is_tesseract_available()

    try:
        if isinstance(image, (bytes, bytearray)):
            image = Image.open(io.BytesIO(image))
        elif not isinstance(image, Image.Image):
            image = Image.open(image)

        text = pytesseract.image_to_string(image)
        return text or ""
    except pytesseract.TesseractNotFoundError:
        raise OCRError(
            "OCR processing failed: Tesseract OCR is not installed or not found in system PATH. "
            "Please install Tesseract-OCR to analyze scanned PDF resumes."
        )
    except pytesseract.TesseractError as err:
        raise OCRError(f"OCR processing failed: {err.message or str(err)}")
    except OCRError:
        raise
    except Exception as err:
        raise OCRError(f"OCR processing failed: {str(err)}")


def extract_images_from_page(page: Any) -> List[Image.Image]:
    """Extract candidate PIL images from a pypdf PageObject.

    Filters out tiny decorative elements (e.g. icons smaller than 50x50).
    """
    images: List[Image.Image] = []
    try:
        page_images = getattr(page, "images", None)
        if not page_images:
            return images

        for img_obj in page_images:
            try:
                img = getattr(img_obj, "image", None)
                if img is None:
                    data = getattr(img_obj, "data", None)
                    if data:
                        img = Image.open(io.BytesIO(data))
                if img is not None:
                    width = getattr(img, "width", 100)
                    height = getattr(img, "height", 100)
                    if width >= 50 and height >= 50:
                        images.append(img)
            except Exception:
                continue
    except Exception:
        return []

    return images


def extract_ocr_from_images(images: List[Image.Image]) -> str:
    """Extract and aggregate text from a list of PIL Images using OCR."""
    ocr_lines = []
    for image in images:
        text = extract_text_from_image(image)
        if text and text.strip():
            ocr_lines.append(text.strip())
    return "\n".join(ocr_lines)


def extract_text_from_scanned_page(page: Any) -> str:
    """Extract text from all scanned images on a single PDF page."""
    images = extract_images_from_page(page)
    return extract_ocr_from_images(images)
