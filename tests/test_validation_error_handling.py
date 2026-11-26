"""Unit and integration tests for Backend Input Validation and Request Error Handling (Issue #60).

Acceptance criteria tested:
- Invalid requests return meaningful error responses (with appropriate HTTP status codes).
- Missing fields are handled safely without crashing.
- Valid resume analysis requests continue working (both browser form and JSON API).
- Internal server details and stack traces are not exposed to users.
"""

import io
import json
import unittest
from unittest.mock import patch

from app import app


def sample_pdf_bytes():
    commands = ["BT /F1 12 Tf 50 780 Td 16 TL"]
    lines = [
        "Synthetic Candidate",
        "candidate@example.com",
        "SKILLS",
        "Python, SQL, Flask",
        "EXPERIENCE",
        "Built REST APIs with Python.",
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


class TestBackendInputValidation(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    # --- Acceptance Criteria 1: Invalid requests return meaningful error responses ---

    def test_api_missing_resume_returns_json_error(self):
        """API client omitting resume file receives 400 Bad Request with JSON error."""
        response = self.client.post(
            "/api/analyze",
            data={},
            headers={"Accept": "application/json"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.is_json)
        data = response.get_json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"], "Please upload a resume.")
        self.assertEqual(data["code"], "MISSING_FILE")
        self.assertEqual(data["status_code"], 400)

    def test_api_empty_filename_returns_json_error(self):
        """API client submitting empty filename receives 400 Bad Request with JSON error."""
        response = self.client.post(
            "/analyze",
            data={"resume": (io.BytesIO(b""), "")},
            content_type="multipart/form-data",
            headers={"Accept": "application/json"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.is_json)
        data = response.get_json()
        self.assertEqual(data["error"], "No file selected.")
        self.assertEqual(data["code"], "EMPTY_FILENAME")

    def test_api_unsupported_file_extension_returns_415(self):
        """API client uploading unsupported file receives 415 with JSON description."""
        response = self.client.post(
            "/api/analyze",
            data={"resume": (io.BytesIO(b"malicious script"), "script.sh")},
            content_type="multipart/form-data",
            headers={"Accept": "application/json"},
        )
        self.assertEqual(response.status_code, 415)
        self.assertTrue(response.is_json)
        data = response.get_json()
        self.assertEqual(data["error"], "Only PDF and DOCX files are allowed.")
        self.assertEqual(data["code"], "UNSUPPORTED_MEDIA_TYPE")

    def test_api_empty_document_text_returns_422(self):
        """Uploading an unreadable / empty PDF returns 422 Unprocessable Entity for API."""
        empty_pdf = (
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] >>\nendobj\n"
            b"xref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000115 00000 n \n"
            b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n185\n%%EOF\n"
        )
        response = self.client.post(
            "/api/analyze",
            data={"resume": (io.BytesIO(empty_pdf), "empty.pdf")},
            content_type="multipart/form-data",
            headers={"Accept": "application/json"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertTrue(response.is_json)
        data = response.get_json()
        self.assertEqual(data["error"], "No readable text found in this PDF.")
        self.assertEqual(data["code"], "EMPTY_DOCUMENT_TEXT")

    # --- Acceptance Criteria 2: Missing fields are handled safely ---

    def test_missing_optional_job_description_handled_safely(self):
        """Omitting optional job_description succeeds without error."""
        response = self.client.post(
            "/api/analyze",
            data={"resume": (io.BytesIO(sample_pdf_bytes()), "resume.pdf")},
            content_type="multipart/form-data",
            headers={"Accept": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertFalse(data["job_match"]["has_job_description"])

    def test_download_report_missing_payload_returns_400(self):
        """Missing report payload returns 400 instead of uncaught exception."""
        response = self.client.post("/download-report", data={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unable to create the report", response.get_data(as_text=True))

        # API client receives JSON error
        api_response = self.client.post(
            "/api/download-report",
            json={},
            headers={"Accept": "application/json"},
        )
        self.assertEqual(api_response.status_code, 400)
        self.assertTrue(api_response.is_json)
        self.assertEqual(api_response.get_json()["code"], "MISSING_REPORT_DATA")

    def test_download_report_malformed_json_returns_400(self):
        """Malformed JSON payload in download-report returns 400."""
        response = self.client.post(
            "/download-report",
            data={"report": "{malformed json syntax"},
        )
        self.assertEqual(response.status_code, 400)

        api_response = self.client.post(
            "/api/download-report",
            data={"report": "{malformed json syntax"},
            headers={"Accept": "application/json"},
        )
        self.assertEqual(api_response.status_code, 400)
        self.assertEqual(api_response.get_json()["code"], "MALFORMED_JSON")

    # --- Acceptance Criteria 3: Valid resume analysis requests continue working ---

    def test_valid_browser_form_request_renders_html(self):
        """Traditional HTML form submission returns 200 OK with full rendered HTML."""
        response = self.client.post(
            "/analyze",
            data={"resume": (io.BytesIO(sample_pdf_bytes()), "resume.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Your Resume Analysis", html)
        self.assertIn("Python", html)

    def test_valid_api_request_returns_structured_json(self):
        """API client receives 200 OK with complete JSON analysis payload."""
        response = self.client.post(
            "/api/analyze",
            data={
                "resume": (io.BytesIO(sample_pdf_bytes()), "resume.pdf"),
                "job_description": "We are seeking a Python and SQL engineer.",
            },
            content_type="multipart/form-data",
            headers={"Accept": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("Python", data["skills"])
        self.assertIn("SQL", data["skills"])
        self.assertIn("score", data)
        self.assertIn("score_breakdown", data)
        self.assertIn("ats_result", data)
        self.assertTrue(data["job_match"]["has_job_description"])

    # --- Acceptance Criteria 4: Internal server details are not exposed to users ---

    def test_unhandled_server_exception_masks_internal_details(self):
        """Internal 500 exceptions do not expose tracebacks, code lines, or system paths."""
        with patch("app.extract_sections", side_effect=ZeroDivisionError("Secret internal math fail in /var/sys/core.py")):
            # Form response
            response = self.client.post(
                "/analyze",
                data={"resume": (io.BytesIO(sample_pdf_bytes()), "resume.pdf")},
                content_type="multipart/form-data",
            )
            self.assertEqual(response.status_code, 200)  # Browser receives safe message
            text = response.get_data(as_text=True)
            self.assertNotIn("ZeroDivisionError", text)
            self.assertNotIn("/var/sys/core.py", text)
            self.assertIn("Unable to analyze this PDF. Please try another PDF.", text)

            # API response
            api_resp = self.client.post(
                "/api/analyze",
                data={"resume": (io.BytesIO(sample_pdf_bytes()), "resume.pdf")},
                content_type="multipart/form-data",
                headers={"Accept": "application/json"},
            )
            self.assertEqual(api_resp.status_code, 422)
            api_data = api_resp.get_json()
            self.assertNotIn("ZeroDivisionError", api_data["error"])
            self.assertNotIn("/var/sys/core.py", api_data["error"])

    def test_404_handler_returns_clean_response(self):
        """Unknown route returns safe 404 response without leaking server paths."""
        response = self.client.get("/nonexistent-endpoint")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("Traceback", response.get_data(as_text=True))

        api_response = self.client.get(
            "/api/nonexistent-endpoint",
            headers={"Accept": "application/json"},
        )
        self.assertEqual(api_response.status_code, 404)
        self.assertTrue(api_response.is_json)
        self.assertEqual(api_response.get_json()["error"], "Resource not found.")

    def test_405_handler_returns_clean_response(self):
        """Method Not Allowed returns safe 405 response."""
        response = self.client.get("/download-report")
        self.assertEqual(response.status_code, 405)

        api_response = self.client.get(
            "/api/download-report",
            headers={"Accept": "application/json"},
        )
        self.assertEqual(api_response.status_code, 405)
        self.assertTrue(api_response.is_json)
        self.assertEqual(api_response.get_json()["code"], "METHOD_NOT_ALLOWED")


if __name__ == "__main__":
    unittest.main()
