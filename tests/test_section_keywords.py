"""Unit and integration tests for Resume Section-wise Keyword Analysis (Issue #59).

Acceptance criteria tested:
- Keywords are grouped by resume section (Skills, Projects, Experience).
- Duplicate keywords across sections are handled consistently.
- Matching keywords in Skills, Projects, and Experience are displayed separately.
- Missing keywords are clearly identified when a job description is provided.
- Existing job description matching remains fully functional.
"""

import io
import unittest

from analyzer.keyword_analyzer import (
    analyze_keywords,
    extract_section_keywords,
)
from app import app


def sample_pdf_bytes():
    commands = ["BT /F1 12 Tf 50 780 Td 16 TL"]
    lines = [
        "Alex Morgan",
        "alex@example.com",
        "SKILLS",
        "Python, SQL, Docker, React",
        "EXPERIENCE",
        "Software Engineer at Synthetix Labs",
        "Built backend microservices using Python and SQL with high performance.",
        "PROJECTS",
        "Resume Analyzer Tool",
        "Created an AI powered web app using Python, Flask, and React.",
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


class SectionKeywordUnitTests(unittest.TestCase):

    def setUp(self):
        self.sections = {
            "skills": "Python, SQL, Docker, React",
            "experience": "Developed scalable microservices using Python and SQL with PostgreSQL.",
            "projects": "Engineered an AI resume analyzer using Python, Flask, and React.",
        }
        self.job_desc = "Seeking a developer skilled in Python, Docker, and Kubernetes."

    def test_keywords_are_grouped_by_section(self):
        """Acceptance Criteria 1: Keywords are grouped by resume section."""
        sec_results, _ = extract_section_keywords(self.sections)

        self.assertIn("skills", sec_results)
        self.assertIn("experience", sec_results)
        self.assertIn("projects", sec_results)

        skills_kws = [k["keyword"] for k in sec_results["skills"]["keywords"]]
        self.assertIn("Python", skills_kws)
        self.assertIn("SQL", skills_kws)
        self.assertIn("Docker", skills_kws)
        self.assertIn("React", skills_kws)

        exp_kws = [k["keyword"] for k in sec_results["experience"]["keywords"]]
        self.assertIn("Python", exp_kws)
        self.assertIn("SQL", exp_kws)
        self.assertIn("PostgreSQL", exp_kws)
        self.assertNotIn("Docker", exp_kws)  # Docker is only in skills

        proj_kws = [k["keyword"] for k in sec_results["projects"]["keywords"]]
        self.assertIn("Python", proj_kws)
        self.assertIn("Flask", proj_kws)
        self.assertIn("React", proj_kws)

    def test_duplicate_keywords_handled_consistently(self):
        """Acceptance Criteria 2: Duplicate keywords across sections are tracked consistently."""
        _, cross_section = extract_section_keywords(self.sections)

        # Python appears in Skills, Experience, and Projects
        python_entry = next((item for item in cross_section if item["keyword"] == "Python"), None)
        self.assertIsNotNone(python_entry)
        self.assertEqual(len(python_entry["section_names"]), 3)
        self.assertIn("Skills", python_entry["section_names"])
        self.assertIn("Work Experience", python_entry["section_names"])
        self.assertIn("Projects", python_entry["section_names"])

        # Check section counts add up to total count
        breakdown = python_entry["section_breakdown"]
        self.assertEqual(sum(breakdown.values()), python_entry["total_count"])

        # Within each section, Python appears once
        sec_results, _ = extract_section_keywords(self.sections)
        for sec in sec_results.values():
            py_counts = [k for k in sec["keywords"] if k["keyword"] == "Python"]
            self.assertLessEqual(len(py_counts), 1)

    def test_matching_and_missing_keywords_with_job_description(self):
        """Acceptance Criteria 3 & 4: Matching and missing keywords are displayed clearly."""
        full_text = (
            "Alex Morgan\nSKILLS\nPython, SQL, Docker, React\n"
            "EXPERIENCE\nDeveloped scalable microservices using Python and SQL.\n"
            "PROJECTS\nAI resume analyzer using Python, Flask, and React."
        )
        result = analyze_keywords(full_text, self.job_desc, resume_sections=self.sections)

        # Existing job match structure remains intact
        job_match = result["job_match"]
        self.assertIsNotNone(job_match)
        matched_job = [m["keyword"] for m in job_match["matched"]]
        missing_job = [m["keyword"] for m in job_match["missing"]]

        self.assertIn("Python", matched_job)
        self.assertIn("Docker", matched_job)
        self.assertIn("Kubernetes", missing_job)

        # Section-wise job match attribution
        sec_results = result["section_keywords"]
        self.assertIn("Python", sec_results["skills"]["matched_job_keywords"])
        self.assertIn("Docker", sec_results["skills"]["matched_job_keywords"])
        self.assertIn("Python", sec_results["experience"]["matched_job_keywords"])
        self.assertNotIn("Docker", sec_results["experience"]["matched_job_keywords"])

    def test_automatic_section_extraction_when_resume_sections_omitted(self):
        """analyze_keywords extracts sections automatically if resume_sections is None."""
        resume_text = (
            "Alex Morgan\n"
            "SKILLS\nPython, SQL, Docker\n"
            "EXPERIENCE\nEngineered backend systems with Python.\n"
            "PROJECTS\nBuilt web applications with Flask.\n"
        )
        result = analyze_keywords(resume_text, "Python and Docker")

        self.assertIn("section_keywords", result)
        self.assertIn("skills", result["section_keywords"])
        self.assertIn("experience", result["section_keywords"])
        self.assertIn("projects", result["section_keywords"])


class SectionKeywordIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_analyze_route_renders_section_wise_keywords(self):
        """Acceptance Criteria 3: Web UI displays section-wise keyword distribution."""
        response = self.client.post(
            "/analyze",
            data={
                "resume": (io.BytesIO(sample_pdf_bytes()), "resume.pdf"),
                "job_description": "We need Python and Docker developer.",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        # Verify section-wise elements are present
        self.assertIn("Section-wise Keyword Distribution", html)
        self.assertIn("Skills", html)
        self.assertIn("Work Experience", html)
        self.assertIn("Projects", html)
        self.assertIn("Cross-Section Keywords", html)

    def test_analyze_route_with_job_description_renders_section_matches(self):
        """Web route /analyze renders section matches and missing keywords when job description is provided."""
        response = self.client.post(
            "/analyze",
            data={
                "resume": (io.BytesIO(sample_pdf_bytes()), "resume.pdf"),
                "job_description": "We need Python, SQL, Docker and Kubernetes developer.",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        self.assertIn("Section-wise Keyword Distribution", html)
        self.assertIn("Skills", html)
        self.assertIn("Work Experience", html)
        self.assertIn("Projects", html)
        # Kubernetes is missing from resume
        self.assertIn("Missing from your resume", html)
        self.assertIn("Kubernetes", html)


if __name__ == "__main__":
    unittest.main()
