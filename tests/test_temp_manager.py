"""Tests for Secure Temporary File Management (Issue #36).

Acceptance criteria tested:
- Temporary files are cleaned up after processing.
- Concurrent uploads do not overwrite each other.
- Failed requests also trigger cleanup.
- Application functionality remains unchanged.
- Personal information is not logged in temporary filenames or outputs.
"""

import concurrent.futures
import io
import os
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from docx import Document
from werkzeug.datastructures import FileStorage

from analyzer.temp_manager import (
    DEFAULT_TEMP_DIR,
    cleanup_stale_temp_files,
    generate_secure_filename,
    get_temp_upload_dir,
    remove_temp_file,
    save_temp_upload,
)
from app import app


def create_sample_docx_bytes():
    doc = Document()
    doc.add_paragraph("Jane Doe | jane@example.com")
    doc.add_paragraph("Skills: Python, Flask, SQL")
    doc.add_paragraph("Experience: Built REST APIs.")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def create_sample_pdf_bytes():
    commands = ["BT /F1 12 Tf 50 780 Td 16 TL"]
    lines = [
        "Jane Doe",
        "jane@example.com",
        "SKILLS",
        "Python, Flask, SQL",
        "EXPERIENCE",
        "Developed scalable web applications.",
    ]
    for line in lines:
        commands.append(f"({line}) Tj T*")
    commands.append("ET")
    stream = "\n".join(commands)

    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] "
        "/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    pdf = "%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{number} 0 obj\n{body}\nendobj\n"

    xref_start = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n"
    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF\n"
    )
    return pdf.encode("latin-1")


class TempManagerUnitTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        cleanup_stale_temp_files(self.temp_dir, max_age_seconds=0)
        try:
            os.rmdir(self.temp_dir)
        except OSError:
            pass

    def test_get_temp_upload_dir_creates_directory(self):
        sub_dir = os.path.join(self.temp_dir, "nested_uploads")
        resolved = get_temp_upload_dir(sub_dir)
        self.assertTrue(os.path.isdir(resolved))
        self.assertEqual(resolved, os.path.abspath(sub_dir))

    def test_generate_secure_filename_omits_pii(self):
        # A user might upload "John_Doe_Confidential_Resume_2026.pdf"
        secure_name = generate_secure_filename(".pdf")
        self.assertTrue(secure_name.startswith("resume_"))
        self.assertTrue(secure_name.endswith(".pdf"))
        self.assertNotIn("John", secure_name)
        self.assertNotIn("Doe", secure_name)

        # Unique across invocations
        name2 = generate_secure_filename(".pdf")
        self.assertNotEqual(secure_name, name2)

    def test_generate_secure_filename_rejects_disallowed_extension(self):
        with self.assertRaises(ValueError):
            generate_secure_filename(".exe")

    def test_save_and_remove_temp_file(self):
        storage = FileStorage(
            stream=io.BytesIO(b"dummy resume content"),
            filename="Jane_Doe_Resume.pdf",
            content_type="application/pdf",
        )
        saved_path = save_temp_upload(storage, directory=self.temp_dir)
        self.assertTrue(os.path.exists(saved_path))
        self.assertNotIn("Jane_Doe", os.path.basename(saved_path))

        # Safe removal
        removed = remove_temp_file(saved_path)
        self.assertTrue(removed)
        self.assertFalse(os.path.exists(saved_path))

    def test_cleanup_stale_temp_files(self):
        old_file = os.path.join(self.temp_dir, "resume_old123.pdf")
        with open(old_file, "w") as f:
            f.write("old data")

        # Set file modification time to 2 hours ago
        two_hours_ago = time.time() - 7200
        os.utime(old_file, (two_hours_ago, two_hours_ago))

        cleaned = cleanup_stale_temp_files(self.temp_dir, max_age_seconds=3600)
        self.assertEqual(cleaned, 1)
        self.assertFalse(os.path.exists(old_file))


class AppTempFileIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.orig_folder = app.config["UPLOAD_FOLDER"]
        app.config["UPLOAD_FOLDER"] = self.temp_dir.name

    def tearDown(self):
        app.config["UPLOAD_FOLDER"] = self.orig_folder
        self.temp_dir.cleanup()

    def assert_temp_dir_empty(self):
        files = os.listdir(app.config["UPLOAD_FOLDER"])
        self.assertEqual(files, [], f"Expected temp directory to be empty, found: {files}")

    def test_successful_pdf_analysis_cleans_up_temporary_file(self):
        """Acceptance Criteria 1: Temporary files are cleaned up after processing."""
        response = self.client.post(
            "/analyze",
            data={"resume": (io.BytesIO(create_sample_pdf_bytes()), "Jane_Doe_Resume.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Your Resume Analysis", response.get_data(as_text=True))
        self.assert_temp_dir_empty()

    def test_successful_docx_analysis_cleans_up_temporary_file(self):
        """Acceptance Criteria 1: Temporary files are cleaned up after processing."""
        response = self.client.post(
            "/analyze",
            data={"resume": (io.BytesIO(create_sample_docx_bytes()), "Jane_Doe_Resume.docx")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Your Resume Analysis", response.get_data(as_text=True))
        self.assert_temp_dir_empty()

    def test_failed_request_invalid_pdf_triggers_cleanup(self):
        """Acceptance Criteria 3: Failed requests also trigger cleanup."""
        response = self.client.post(
            "/analyze",
            data={"resume": (io.BytesIO(b"corrupted raw data not a pdf"), "corrupt.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Unable to analyze this PDF", response.get_data(as_text=True))
        self.assert_temp_dir_empty()

    def test_failed_request_invalid_docx_triggers_cleanup(self):
        """Acceptance Criteria 3: Failed requests also trigger cleanup."""
        response = self.client.post(
            "/analyze",
            data={"resume": (io.BytesIO(b"not really a zip or word file"), "corrupt.docx")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("This file is not a valid DOCX document.", response.get_data(as_text=True))
        self.assert_temp_dir_empty()

    def test_failed_request_empty_text_triggers_cleanup(self):
        """Acceptance Criteria 3: Empty text resumes trigger cleanup."""
        # PDF with valid structure but empty text
        empty_pdf = (
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] >>\nendobj\n"
            b"xref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000115 00000 n \n"
            b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n185\n%%EOF\n"
        )
        response = self.client.post(
            "/analyze",
            data={"resume": (io.BytesIO(empty_pdf), "empty.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("No readable text found in this PDF.", response.get_data(as_text=True))
        self.assert_temp_dir_empty()

    def test_failed_request_analysis_exception_triggers_cleanup(self):
        """Acceptance Criteria 3: Unexpected exceptions during processing trigger cleanup."""
        with patch("app.extract_sections", side_effect=RuntimeError("Simulated pipeline crash")):
            response = self.client.post(
                "/analyze",
                data={"resume": (io.BytesIO(create_sample_pdf_bytes()), "resume.pdf")},
                content_type="multipart/form-data",
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("Unable to analyze this PDF.", response.get_data(as_text=True))
            self.assert_temp_dir_empty()

    def test_concurrent_uploads_do_not_overwrite_each_other(self):
        """Acceptance Criteria 2: Concurrent uploads do not overwrite each other."""
        num_requests = 10
        saved_paths_seen = set()

        # Intercept file.save in app to record saved file paths during concurrent requests
        original_save = FileStorage.save

        def recording_save(storage_self, dst, *args, **kwargs):
            saved_paths_seen.add(dst)
            return original_save(storage_self, dst, *args, **kwargs)

        with patch.object(FileStorage, "save", side_effect=recording_save, autospec=True):
            def send_upload(i):
                client = app.test_client()
                # All uploads use identical filename "resume.pdf"
                pdf_bytes = create_sample_pdf_bytes()
                return client.post(
                    "/analyze",
                    data={"resume": (io.BytesIO(pdf_bytes), "resume.pdf")},
                    content_type="multipart/form-data",
                )

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                responses = list(executor.map(send_upload, range(num_requests)))

        # Every request succeeded
        for resp in responses:
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Your Resume Analysis", resp.get_data(as_text=True))

        # Every concurrent request was assigned a distinct, unique temporary filename
        self.assertEqual(len(saved_paths_seen), num_requests)

        # All temporary files were cleaned up after completion
        self.assert_temp_dir_empty()


if __name__ == "__main__":
    unittest.main()
