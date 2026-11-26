"""Unit tests for OCR support on scanned PDF resumes (Issue #32).

Acceptance criteria tested:
- Scanned PDF pages can be processed.
- Regular text-based PDFs continue using normal extraction.
- OCR failures display understandable errors.
- Extracted text is passed to the same analysis pipeline.
"""

import io
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from fpdf import FPDF
from PIL import Image
import pytesseract

from analyzer.ocr import (
    OCRError,
    extract_images_from_page,
    extract_ocr_from_images,
    extract_text_from_image,
    extract_text_from_scanned_page,
    is_tesseract_available,
)
from analyzer.resume_extractor import (
    extract_pdf_text,
    extract_resume_text,
)
from app import app


def create_image_file(path: str, width: int = 200, height: int = 200, color: str = "white"):
    """Helper to create a temporary test image on disk."""
    Image.new("RGB", (width, height), color=color).save(path)


def create_scanned_pdf(pdf_path: str, img_path: str):
    """Helper to create a PDF containing an embedded image (scanned page)."""
    pdf = FPDF()
    pdf.add_page()
    pdf.image(img_path, x=10, y=10, w=100)
    pdf.output(pdf_path)


def create_text_pdf(pdf_path: str, content: str):
    """Helper to create a regular text-based PDF."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    for line in content.split("\n"):
        pdf.cell(0, 10, line, new_x="LMARGIN", new_y="NEXT")
    pdf.output(pdf_path)


class OCRUnitTests(unittest.TestCase):

    def test_extract_text_from_image_success(self):
        """Test successful OCR extraction on a PIL image."""
        img = Image.new("RGB", (100, 100), color="white")
        with patch("pytesseract.image_to_string", return_value="Extracted OCR text"):
            result = extract_text_from_image(img)
            self.assertEqual(result, "Extracted OCR text")

    def test_extract_text_from_image_tesseract_not_found(self):
        """Acceptance Criteria 3: OCR failures display understandable errors (Tesseract not in PATH)."""
        img = Image.new("RGB", (100, 100), color="white")
        with patch("pytesseract.image_to_string", side_effect=pytesseract.TesseractNotFoundError()):
            with self.assertRaises(OCRError) as ctx:
                extract_text_from_image(img)
            self.assertIn("Tesseract OCR is not installed or not found", str(ctx.exception))
            self.assertIn("Please install Tesseract-OCR", str(ctx.exception))

    def test_extract_text_from_image_tesseract_execution_error(self):
        """Acceptance Criteria 3: OCR failures display understandable errors (TesseractError)."""
        img = Image.new("RGB", (100, 100), color="white")
        mock_err = pytesseract.TesseractError(1, "Processing failed")
        with patch("pytesseract.image_to_string", side_effect=mock_err):
            with self.assertRaises(OCRError) as ctx:
                extract_text_from_image(img)
            self.assertIn("OCR processing failed", str(ctx.exception))

    def test_extract_text_from_image_missing_pytesseract(self):
        """Acceptance Criteria 3: Understandable error when pytesseract is not installed."""
        img = Image.new("RGB", (100, 100), color="white")
        with patch("analyzer.ocr.pytesseract", None):
            with self.assertRaises(OCRError) as ctx:
                extract_text_from_image(img)
            self.assertIn("pytesseract is not installed", str(ctx.exception))

    def test_filters_out_tiny_decorative_icons(self):
        """Icons/dividers smaller than 50x50 are ignored to avoid unnecessary OCR calls."""
        mock_page = MagicMock()
        tiny_img = MagicMock()
        tiny_img.image = Image.new("RGB", (16, 16), color="black")

        large_img = MagicMock()
        large_img.image = Image.new("RGB", (300, 400), color="white")

        mock_page.images = [tiny_img, large_img]
        images = extract_images_from_page(mock_page)

        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].size, (300, 400))


class ScannedPDFExtractionTests(unittest.TestCase):

    def test_scanned_pdf_pages_can_be_processed(self):
        """Acceptance Criteria 1: Scanned PDF pages can be processed."""
        with tempfile.TemporaryDirectory() as td:
            img_path = os.path.join(td, "scan.png")
            pdf_path = os.path.join(td, "scanned_resume.pdf")

            create_image_file(img_path, 300, 300)
            create_scanned_pdf(pdf_path, img_path)

            mock_ocr_text = (
                "Jane Doe\n"
                "jane@example.com | +1 555 123 4567\n"
                "SKILLS: Python, Flask, SQL, Docker\n"
                "EXPERIENCE: Senior Backend Developer\n"
            )

            with patch("pytesseract.image_to_string", return_value=mock_ocr_text):
                extracted_text = extract_pdf_text(pdf_path)

            self.assertIn("Jane Doe", extracted_text)
            self.assertIn("Python", extracted_text)
            self.assertIn("Docker", extracted_text)

    def test_regular_text_pdf_continues_using_normal_extraction(self):
        """Acceptance Criteria 2: Regular text-based PDFs continue using normal extraction."""
        with tempfile.TemporaryDirectory() as td:
            pdf_path = os.path.join(td, "text_resume.pdf")
            content = (
                "John Smith\n"
                "john.smith@example.com\n"
                "Software Engineer with 5 years experience in Python and Cloud Systems."
            )
            create_text_pdf(pdf_path, content)

            with patch("pytesseract.image_to_string") as mock_ocr:
                extracted_text = extract_pdf_text(pdf_path)
                # pytesseract must NOT be called for regular text-based PDFs
                mock_ocr.assert_not_called()

            self.assertIn("John Smith", extracted_text)
            self.assertIn("Python", extracted_text)

    def test_mixed_pdf_extracts_text_and_applies_ocr_to_scanned_page(self):
        """Test multi-page PDF where page 1 has text and page 2 is a scanned image."""
        with tempfile.TemporaryDirectory() as td:
            img_path = os.path.join(td, "scan_page2.png")
            pdf_path = os.path.join(td, "mixed_resume.pdf")
            create_image_file(img_path, 300, 300)

            # Build 2-page PDF: Page 1 text, Page 2 image
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=12)
            pdf.cell(0, 10, "Page 1: Full Candidate Profile and Work History Details", new_x="LMARGIN", new_y="NEXT")

            pdf.add_page()
            pdf.image(img_path, x=10, y=10, w=100)
            pdf.output(pdf_path)

            mock_p2_text = "Page 2 Scanned Certifications: Certified Kubernetes Administrator"

            with patch("pytesseract.image_to_string", return_value=mock_p2_text) as mock_ocr:
                extracted_text = extract_pdf_text(pdf_path)
                # OCR called exactly once (for page 2 scanned image)
                self.assertEqual(mock_ocr.call_count, 1)

            self.assertIn("Page 1: Full Candidate Profile", extracted_text)
            self.assertIn("Certified Kubernetes Administrator", extracted_text)

    def test_ocr_failure_raises_understandable_error_in_extractor(self):
        """Acceptance Criteria 3: OCR failures raise understandable error during extraction."""
        with tempfile.TemporaryDirectory() as td:
            img_path = os.path.join(td, "scan.png")
            pdf_path = os.path.join(td, "scanned.pdf")
            create_image_file(img_path, 300, 300)
            create_scanned_pdf(pdf_path, img_path)

            with patch("pytesseract.image_to_string", side_effect=pytesseract.TesseractNotFoundError()):
                with self.assertRaises(OCRError) as ctx:
                    extract_resume_text(pdf_path)
                self.assertIn("Tesseract OCR is not installed or not found in system PATH", str(ctx.exception))


class AppScannedPDFIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        self.files_before = set(os.listdir(app.config["UPLOAD_FOLDER"]))

    def tearDown(self):
        # Ensure temporary uploads are cleaned up
        files_now = set(os.listdir(app.config["UPLOAD_FOLDER"]))
        self.assertEqual(files_now - self.files_before, set())

    def test_scanned_pdf_passes_into_existing_analysis_pipeline(self):
        """Acceptance Criteria 4: Extracted text is passed to the same analysis pipeline."""
        with tempfile.TemporaryDirectory() as td:
            img_path = os.path.join(td, "scan.png")
            pdf_path = os.path.join(td, "scanned_resume.pdf")
            create_image_file(img_path, 300, 300)
            create_scanned_pdf(pdf_path, img_path)

            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            mock_resume_text = (
                "Jane Doe\n"
                "jane@example.com | +1 555-123-4567\n"
                "PROFESSIONAL SUMMARY\n"
                "Software Engineer specializing in Python web services.\n"
                "SKILLS\n"
                "Python, Flask, SQL, Docker, Git\n"
                "EDUCATION\n"
                "B.S. in Computer Science\n"
                "EXPERIENCE\n"
                "Backend Engineer at TechCorp\n"
            )

            with patch("pytesseract.image_to_string", return_value=mock_resume_text):
                response = self.client.post(
                    "/analyze",
                    data={"resume": (io.BytesIO(pdf_bytes), "scanned_resume.pdf")},
                    content_type="multipart/form-data",
                )

            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)

            # Verifies standard analysis pipeline was executed:
            self.assertIn("ATS Compatibility Analysis", html)
            self.assertIn("Python", html)
            self.assertIn("Flask", html)
            self.assertIn("Resume Score", html)

    def test_scanned_pdf_ocr_failure_shows_understandable_error(self):
        """Acceptance Criteria 3: OCR failure during web upload shows understandable error."""
        with tempfile.TemporaryDirectory() as td:
            img_path = os.path.join(td, "scan.png")
            pdf_path = os.path.join(td, "scanned_resume.pdf")
            create_image_file(img_path, 300, 300)
            create_scanned_pdf(pdf_path, img_path)

            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            with patch("pytesseract.image_to_string", side_effect=pytesseract.TesseractNotFoundError()):
                response = self.client.post(
                    "/analyze",
                    data={"resume": (io.BytesIO(pdf_bytes), "scanned_resume.pdf")},
                    content_type="multipart/form-data",
                )

            self.assertEqual(response.status_code, 200)
            message = response.get_data(as_text=True)
            self.assertIn("OCR processing failed: Tesseract OCR is not installed", message)
            self.assertIn("Please install Tesseract-OCR", message)


if __name__ == "__main__":
    unittest.main()
