"""Unit and integration tests for Certification and Achievement Detection (Issue #56).

Verifies:
1. Common certification and achievement headings and content are detected.
2. Missing sections are handled gracefully without error.
3. Duplicate entries are avoided.
4. Individual entries are cleanly extracted (removing bullet markers, excess whitespace).
5. Existing skill extraction continues working seamlessly.
6. Integration with web analysis workflow and result rendering.
"""

import io
import unittest

from analyzer.credentials_detector import (
    detect_achievements,
    detect_certifications,
    extract_achievement_entries,
    extract_certification_entries,
)
from analyzer.section_detector import extract_sections, normalize_heading
from analyzer.skills_extractor import extract_skills
from app import app


def sample_pdf_bytes_with_credentials():
    """Build a tiny valid PDF containing certifications and achievements."""
    lines = [
        "Alex Morgan",
        "alex@example.com",
        "SKILLS",
        "Python, Docker, SQL",
        "CERTIFICATIONS",
        "- AWS Certified Solutions Architect - Associate",
        "- Certified Kubernetes Administrator (CKA)",
        "ACHIEVEMENTS",
        "1. 1st Place Winner at Global AI Hackathon 2024",
        "2. Dean's List for Academic Excellence",
        "EXPERIENCE",
        "Software Engineer at Acme Corp",
    ]
    commands = ["BT /F1 12 Tf 50 780 Td 16 TL"]
    for line in lines:
        safe = line.replace("(", "").replace(")", "")
        commands.append(f"({safe}) Tj T*")
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


class TestHeadingDetection(unittest.TestCase):
    """Verify common certification and achievement heading variations are detected."""

    def test_certification_headings(self):
        headings = [
            "Certifications",
            "CERTIFICATIONS",
            "Professional Certifications",
            "Licenses & Certifications",
            "Licenses and Certifications",
            "Certificates",
            "Online Courses",
            "Accreditations",
            "Credentials",
        ]
        for h in headings:
            with self.subTest(heading=h):
                self.assertEqual(normalize_heading(h), "certifications")

    def test_achievement_headings(self):
        headings = [
            "Achievements",
            "ACHIEVEMENTS",
            "Key Achievements",
            "Awards",
            "Honors & Awards",
            "Honors and Awards",
            "Awards and Achievements",
            "Accomplishments",
            "Accolades",
            "Recognitions",
        ]
        for h in headings:
            with self.subTest(heading=h):
                self.assertEqual(normalize_heading(h), "achievements")


class TestEntryExtraction(unittest.TestCase):
    """Verify entry extraction, cleaning, and duplicate prevention."""

    def test_extract_certification_entries(self):
        text = """
        • AWS Certified Solutions Architect - Associate
        - Certified Kubernetes Administrator (CKA)
        1. Meta Front-End Developer Professional Certificate
        """
        entries = extract_certification_entries(text)
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0], "AWS Certified Solutions Architect - Associate")
        self.assertEqual(entries[1], "Certified Kubernetes Administrator (CKA)")
        self.assertEqual(entries[2], "Meta Front-End Developer Professional Certificate")

    def test_extract_achievement_entries(self):
        text = """
        * 1st Place at National Smart India Hackathon
        2. Best Innovation Award at TechFest 2023
        - Dean's Honor Roll for 4 consecutive semesters
        """
        entries = extract_achievement_entries(text)
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0], "1st Place at National Smart India Hackathon")
        self.assertEqual(entries[1], "Best Innovation Award at TechFest 2023")
        self.assertEqual(entries[2], "Dean's Honor Roll for 4 consecutive semesters")

    def test_duplicate_entries_are_avoided(self):
        text = """
        • AWS Certified Solutions Architect
        • aws certified solutions architect
        • AWS Certified Solutions Architect
        • CompTIA Security+
        """
        entries = extract_certification_entries(text)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0], "AWS Certified Solutions Architect")
        self.assertEqual(entries[1], "CompTIA Security+")

    def test_single_line_semicolon_delimited_entries(self):
        text = "AWS Certified Developer; Certified Ethical Hacker; CompTIA Security+"
        entries = extract_certification_entries(text)
        self.assertEqual(len(entries), 3)
        self.assertIn("AWS Certified Developer", entries)
        self.assertIn("Certified Ethical Hacker", entries)
        self.assertIn("CompTIA Security+", entries)


class TestGracefulHandlingMissingSections(unittest.TestCase):
    """Verify missing sections are handled gracefully."""

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(detect_certifications(""), [])
        self.assertEqual(detect_certifications(None), [])
        self.assertEqual(detect_achievements(""), [])
        self.assertEqual(detect_achievements(None), [])

    def test_resume_without_credentials(self):
        text = """
        Jane Doe
        SKILLS
        Python, Flask
        EXPERIENCE
        Software engineer at Acme.
        """
        sections = extract_sections(text)
        certs = detect_certifications(text, sections)
        achs = detect_achievements(text, sections)
        self.assertEqual(certs, [])
        self.assertEqual(achs, [])


class TestSkillExtractionContinuity(unittest.TestCase):
    """Verify existing skill extraction continues working when credentials are present."""

    def test_skills_still_extracted_properly(self):
        text = """
        John Doe
        SKILLS
        Python, Docker, SQL, Kubernetes, Git
        CERTIFICATIONS
        • AWS Certified Solutions Architect
        ACHIEVEMENTS
        • Won 1st place in Coding Challenge
        """
        skills = extract_skills(text)
        self.assertIn("Python", skills)
        self.assertIn("Docker", skills)
        self.assertIn("SQL", skills)
        self.assertIn("Kubernetes", skills)
        self.assertIn("Git", skills)
        self.assertIn("AWS", skills)


class TestWebAnalysisIntegration(unittest.TestCase):
    """Verify the /analyze route renders certifications and achievements separately."""

    def setUp(self):
        self.client = app.test_client()

    def test_analyze_route_renders_certifications_and_achievements(self):
        pdf_bytes = sample_pdf_bytes_with_credentials()
        response = self.client.post(
            "/analyze",
            data={"resume": (io.BytesIO(pdf_bytes), "resume.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        # Certifications card and items
        self.assertIn("Certifications", html)
        self.assertIn("AWS Certified Solutions Architect", html)
        self.assertIn("Certified Kubernetes Administrator", html)

        # Achievements card and items
        self.assertIn("Achievements & Awards", html)
        self.assertIn("Global AI Hackathon", html)
        self.assertIn("Academic Excellence", html)

        # Both sections exist separately
        self.assertIn("📜", html)
        self.assertIn("🏆", html)


if __name__ == "__main__":
    unittest.main()
