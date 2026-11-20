import unittest
from analyzer.section_quality import analyze_section_quality


class TestResumeSectionQualityAnalysis(unittest.TestCase):

    def test_empty_resume(self):
        result = analyze_section_quality("")
        self.assertEqual(result["sections"], {})
        self.assertEqual(result["summary"]["overall_quality"], "No Content")

    def test_none_sections_handled_without_attribute_error(self):
        null_sections = {"education": None, "skills": None, "projects": None, "experience": None}
        result = analyze_section_quality("some text", resume_sections=null_sections)
        self.assertIn("education", result["sections"])
        self.assertEqual(result["sections"]["education"]["status"], "Missing")


    def test_complete_resume_sections(self):
        text = """
        John Doe
        john@example.com | 1234567890

        EDUCATION
        B.Tech in Computer Science and Engineering
        Apex University, 2021 - 2025
        CGPA: 8.9 / 10

        SKILLS
        Languages: Python, JavaScript, Java, C++
        Frameworks: Flask, Django, React, Node.js
        Databases: PostgreSQL, MongoDB

        PROJECTS
        AI Resume Analyzer | Python, Flask, React
        • Built an automated resume evaluation tool to detect ATS issues and extract skills.
        • Implemented REST APIs and optimized query performance.

        EXPERIENCE
        Software Engineering Intern, Tech Solutions (Jun 2024 - Aug 2024)
        • Developed full-stack features using Flask and PostgreSQL.
        • Collaborated with senior engineers to deploy containerized microservices.
        """
        result = analyze_section_quality(text)
        sections = result["sections"]

        self.assertIn("education", sections)
        self.assertIn("skills", sections)
        self.assertIn("projects", sections)
        self.assertIn("experience", sections)

        self.assertEqual(sections["education"]["status"], "Complete")
        self.assertEqual(sections["skills"]["status"], "Complete")
        self.assertEqual(sections["projects"]["status"], "Complete")
        self.assertEqual(sections["experience"]["status"], "Complete")
        self.assertEqual(result["summary"]["overall_quality"], "Strong")

    def test_incomplete_education_section(self):
        text = """
        EDUCATION
        Schooling done
        """
        result = analyze_section_quality(text)
        edu = result["sections"]["education"]
        self.assertTrue(edu["present"])
        self.assertEqual(edu["status"], "Needs Detail")
        self.assertTrue(len(edu["gaps"]) > 0)
        self.assertTrue(any("degree" in g.lower() for g in edu["gaps"]))
        self.assertTrue(any("institution" in g.lower() or "university" in g.lower() for g in edu["gaps"]))
        self.assertTrue(any("graduation" in s.lower() or "degree" in s.lower() for s in edu["suggestions"]))

    def test_incomplete_skills_section(self):
        text = """
        SKILLS
        Good worker
        """
        result = analyze_section_quality(text)
        skills = result["sections"]["skills"]
        self.assertTrue(skills["present"])
        self.assertEqual(skills["status"], "Needs Detail")
        self.assertTrue(len(skills["gaps"]) > 0)
        self.assertTrue(len(skills["suggestions"]) > 0)

    def test_incomplete_projects_section(self):
        text = """
        PROJECTS
        Simple calculator
        """
        result = analyze_section_quality(text)
        proj = result["sections"]["projects"]
        self.assertTrue(proj["present"])
        self.assertEqual(proj["status"], "Needs Detail")
        self.assertTrue(any("brief" in g.lower() for g in proj["gaps"]))
        self.assertTrue(any("technologies" in s.lower() or "verbs" in s.lower() or "expand" in s.lower() for s in proj["suggestions"]))

    def test_optional_experience_not_treated_as_mandatory(self):
        # A fresher resume without experience section
        text = """
        John Doe
        john@example.com

        EDUCATION
        B.Tech in Computer Science, Apex University, 2021 - 2025

        SKILLS
        Languages: Python, Java, C++, SQL | Frameworks: Flask, React

        PROJECTS
        Personal Portfolio: Built personal website using React and HTML.
        """
        result = analyze_section_quality(text)
        exp = result["sections"]["experience"]
        self.assertFalse(exp["present"])
        self.assertTrue(exp["is_optional"])
        self.assertEqual(exp["status"], "Not Included (Optional)")
        self.assertEqual(exp["gaps"], [])
        self.assertTrue(len(exp["suggestions"]) > 0)

    def test_optional_sections_analyzed_when_present(self):
        text = """
        John Doe

        SUMMARY
        Passionate software developer with a strong foundation in backend development and cloud technologies.

        EDUCATION
        B.S. in Computer Science, City College, 2020 - 2024

        SKILLS
        Python, Flask, Docker, PostgreSQL

        PROJECTS
        Task Manager: Developed a task management web app using Python and Flask.

        CERTIFICATIONS
        AWS Certified Cloud Practitioner (2024)
        """
        result = analyze_section_quality(text)
        sections = result["sections"]
        self.assertIn("summary", sections)
        self.assertIn("certifications", sections)
        self.assertTrue(sections["summary"]["present"])
        self.assertTrue(sections["certifications"]["present"])

    def test_original_text_remains_unchanged(self):
        original = "EDUCATION\nB.Tech Computer Science, 2025\nSKILLS\nPython, SQL"
        copied = str(original)
        analyze_section_quality(copied)
        self.assertEqual(copied, original)


    def test_flask_integration(self):
        import io
        from unittest.mock import patch
        from app import app

        test_client = app.test_client()
        resume_content = """
        John Doe
        john@example.com

        EDUCATION
        B.Tech Computer Science, Apex University, 2021 - 2025

        SKILLS
        Python, Flask, SQL, Git

        PROJECTS
        AI Resume Analyzer | Python
        Built an automated resume evaluation tool to detect ATS issues.
        """
        data = {
            "resume": (io.BytesIO(b"%PDF-1.4 test"), "test_resume.pdf"),
        }

        with patch("app.extract_resume_text", return_value=resume_content):
            response = test_client.post("/analyze", data=data, content_type="multipart/form-data")
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Section Quality & Completeness", response.data)
            self.assertIn(b"Education", response.data)


if __name__ == "__main__":
    unittest.main()
