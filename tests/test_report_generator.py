import io
import json
import unittest

from pypdf import PdfReader

from analyzer.report_generator import build_report, build_txt_report
from app import app

DATA = {
    "score": 82,
    "breakdown": {"Contact Information": 10, "Technical Skills": 14},
    "skills": ["Python", "Flask"],
    "suggestions": ["Add Git experience if applicable."],
    "recommendations": [
        {
            "section": "Projects",
            "tips": [
                {
                    "tip": "Say what technologies you used in each project.",
                    "example": "Project Alpha: built with Python and Flask.",
                }
            ],
        }
    ],
    "job_match": {
        "has_job_description": True,
        "match_percentage": 40,
        "total_matching": 2,
        "total_required": 5,
        "matching_skills": ["Python", "Flask"],
        "missing_skills": ["Docker"],
    },
}


def pdf_text(pdf_bytes):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() for page in reader.pages)


class ReportTests(unittest.TestCase):

    def test_report_contains_the_results(self):
        pdf = build_report(DATA)
        text = pdf_text(pdf)

        self.assertTrue(pdf.startswith(b"%PDF"))
        for expected in ("82 / 100", "Contact Information", "14 / 20", "Python, Flask",
                         "Add Git experience", "40% match", "Docker"):
            self.assertIn(expected, text)

    def test_job_section_is_skipped_without_a_job_description(self):
        without = dict(DATA, job_match={"has_job_description": False})
        missing_key = {k: v for k, v in DATA.items() if k != "job_match"}

        self.assertNotIn("Job Description Match", pdf_text(build_report(without)))
        self.assertNotIn("Job Description Match", pdf_text(build_report(missing_key)))

    def test_empty_data_still_gives_a_valid_report(self):
        text = pdf_text(build_report({}))
        self.assertIn("Resume Analysis Report", text)
        self.assertIn("No matching skills detected.", text)

    def test_non_latin_text_does_not_crash(self):
        data = dict(DATA, skills=["Python", "हिन्दी", "😀"])
        self.assertIn("Python", pdf_text(build_report(data)))


class TxtReportTests(unittest.TestCase):

    def test_txt_report_contains_all_core_sections(self):
        txt = build_txt_report(DATA)
        self.assertIsInstance(txt, str)
        # Headings
        self.assertIn("RESUME ANALYSIS REPORT", txt)
        self.assertIn("OVERALL RESUME SCORE", txt)
        self.assertIn("SKILLS DETECTED", txt)
        self.assertIn("RECOMMENDATIONS & SUGGESTIONS", txt)
        self.assertIn("JOB DESCRIPTION MATCH", txt)

        # Content matches analysis data
        self.assertIn("82 / 100", txt)
        self.assertIn("Contact Information: 10 / 10", txt)
        self.assertIn("Technical Skills: 14 / 20", txt)
        self.assertIn("Python, Flask", txt)
        self.assertIn("Add Git experience if applicable.", txt)
        self.assertIn("[Projects]", txt)
        self.assertIn("Say what technologies you used in each project.", txt)
        self.assertIn("Project Alpha: built with Python and Flask.", txt)
        self.assertIn("Match Score: 40%", txt)
        self.assertIn("Docker", txt)

    def test_txt_report_handles_empty_sections_safely(self):
        txt = build_txt_report({})
        self.assertIn("RESUME ANALYSIS REPORT", txt)
        self.assertIn("0 / 100", txt)
        self.assertIn("(No breakdown details available)", txt)
        self.assertIn("No matching skills detected.", txt)
        self.assertIn("No recommendations needed", txt)
        self.assertNotIn("JOB DESCRIPTION MATCH", txt)

    def test_txt_report_handles_special_characters_cleanly(self):
        special_data = {
            "score": 90,
            "skills": ["C++", "C#", "Node.js", "Python (3.11)", "R&D", "Résumé Expert • Special ✦"],
            "suggestions": ["Include Café & résumé accomplishments — 100% verified ✔."],
        }
        txt = build_txt_report(special_data)
        encoded = txt.encode("utf-8")
        decoded = encoded.decode("utf-8")
        self.assertEqual(txt, decoded)
        self.assertIn("Résumé Expert • Special ✦", txt)
        self.assertIn("Café & résumé accomplishments — 100% verified ✔", txt)

    def test_txt_report_skips_job_section_when_no_job_description(self):
        without = dict(DATA, job_match={"has_job_description": False})
        txt = build_txt_report(without)
        self.assertNotIn("JOB DESCRIPTION MATCH", txt)


class DownloadRouteTests(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_download_returns_a_pdf_file(self):
        response = self.client.post("/download-report", data={"report": json.dumps(DATA)})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertIn("attachment", response.headers["Content-Disposition"])
        self.assertTrue(response.data.startswith(b"%PDF"))

    def test_download_txt_returns_a_txt_file(self):
        response = self.client.post("/download-txt-report", data={"report": json.dumps(DATA)})

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response.mimetype)
        self.assertIn("attachment", response.headers["Content-Disposition"])
        self.assertIn("resume-analysis-report.txt", response.headers["Content-Disposition"])

        content = response.data.decode("utf-8")
        self.assertIn("RESUME ANALYSIS REPORT", content)
        self.assertIn("Score: 82 / 100", content)
        self.assertIn("Python, Flask", content)
        self.assertIn("Say what technologies you used", content)

    def test_bad_data_gives_a_clear_error(self):
        for bad in ("not json", "[1, 2]"):
            response_pdf = self.client.post("/download-report", data={"report": bad})
            self.assertEqual(response_pdf.status_code, 400)
            response_txt = self.client.post("/download-txt-report", data={"report": bad})
            self.assertEqual(response_txt.status_code, 400)

        self.assertEqual(self.client.post("/download-report").status_code, 400)
        self.assertEqual(self.client.post("/download-txt-report").status_code, 400)


if __name__ == "__main__":
    unittest.main()
