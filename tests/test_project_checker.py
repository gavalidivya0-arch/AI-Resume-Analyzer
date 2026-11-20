import unittest
from analyzer.project_checker import check_project_descriptions, SAMPLE_TEMPLATES


class TestProjectDescriptionQualityChecker(unittest.TestCase):

    def test_empty_resume_text(self):
        result = check_project_descriptions("")
        self.assertEqual(result["total_projects"], 0)
        self.assertEqual(result["quality_score"], 0)
        self.assertEqual(result["projects"], [])
        self.assertTrue(len(result["general_suggestions"]) > 0)
        self.assertTrue(len(result["sample_templates"]) > 0)

    def test_none_inputs_handled_safely(self):
        result = check_project_descriptions(None, resume_sections={"projects": None})
        self.assertEqual(result["total_projects"], 0)
        self.assertEqual(result["quality_score"], 0)


    def test_no_projects_section(self):
        text = """
        John Doe
        john@example.com

        EXPERIENCE
        Software Engineer at Acme Corp (2021 - 2023)
        Built backend microservices.

        SKILLS
        Python, Flask, Docker
        """
        result = check_project_descriptions(text)
        self.assertEqual(result["total_projects"], 0)
        self.assertIn("No dedicated Projects section was detected.", result["general_suggestions"][0])

    def test_detects_multiple_projects(self):
        text = """
        John Doe

        PROJECTS
        AI Resume Analyzer | Python, Flask, React
        • Developed a web application designed to evaluate candidate resumes against ATS standards.
        • Implemented REST APIs and optimized parsing algorithms, improving speed by 35%.

        E-Commerce Mobile App (Flutter, Firebase)
        • Built an online store allowing students to buy and sell textbooks.
        • Designed secure authentication and real-time database syncing.
        """
        result = check_project_descriptions(text)
        self.assertEqual(result["total_projects"], 2)
        p1 = result["projects"][0]
        p2 = result["projects"][1]

        self.assertIn("AI Resume Analyzer", p1["title"])
        self.assertTrue(p1["has_technologies"])
        self.assertIn("Python", p1["technologies"])
        self.assertTrue(p1["has_objective"])
        self.assertTrue(p1["has_contributions"])
        self.assertTrue(p1["has_metrics"])
        self.assertEqual(p1["quality_status"], "Detailed & Strong")

        self.assertIn("E-Commerce Mobile App", p2["title"])
        self.assertTrue(p2["has_objective"])
        self.assertTrue(p2["has_contributions"])

    def test_missing_technologies_highlighted(self):
        text = """
        PROJECTS
        Chat Application
        Developed an instant messaging system designed to connect local community members.
        Designed the interface and created user login workflows.
        """
        sections = {"projects": text}
        result = check_project_descriptions(text, resume_sections=sections)
        self.assertEqual(result["total_projects"], 1)
        p = result["projects"][0]

        self.assertFalse(p["has_technologies"])
        self.assertTrue(any("Technologies" in m for m in p["missing_details"]))
        self.assertTrue(any(s["focus"] == "Add Technologies" for s in p["wording_suggestions"]))

    def test_missing_objective_highlighted(self):
        text = """
        PROJECTS
        Data Pipeline | Python, SQL, Docker
        Implemented daily ETL cron jobs using Python and PostgreSQL.
        Configured Docker containers and established unit test suites.
        """
        sections = {"projects": text}
        result = check_project_descriptions(text, resume_sections=sections)
        self.assertEqual(result["total_projects"], 1)
        p = result["projects"][0]

        self.assertTrue(p["has_technologies"])
        self.assertFalse(p["has_objective"])
        self.assertTrue(any("Objective" in m for m in p["missing_details"]))
        self.assertTrue(any(s["focus"] == "Define Objective" for s in p["wording_suggestions"]))

    def test_missing_contributions_highlighted(self):
        text = """
        PROJECTS
        Weather Dashboard
        A responsive web dashboard to monitor local atmospheric conditions and weather forecasts.
        Tech Stack: React, JavaScript.
        """
        sections = {"projects": text}
        result = check_project_descriptions(text, resume_sections=sections)
        self.assertEqual(result["total_projects"], 1)
        p = result["projects"][0]

        self.assertTrue(p["has_technologies"])
        self.assertTrue(p["has_objective"])
        self.assertFalse(p["has_contributions"])
        self.assertTrue(any("Contributions" in m for m in p["missing_details"]))
        self.assertTrue(any(s["focus"] == "Highlight Contributions" for s in p["wording_suggestions"]))

    def test_brief_description_flagged(self):
        text = """
        PROJECTS
        Portfolio
        Made with HTML and CSS.
        """
        sections = {"projects": text}
        result = check_project_descriptions(text, resume_sections=sections)
        self.assertEqual(result["total_projects"], 1)
        p = result["projects"][0]
        self.assertTrue(any("brief" in m.lower() for m in p["missing_details"]))
        self.assertEqual(p["quality_status"], "Needs Improvement")

    def test_sample_wording_suggestions_use_placeholders(self):
        text = """
        PROJECTS
        Simple Blog
        Made a basic website.
        """
        result = check_project_descriptions(text)
        p = result["projects"][0]
        # Suggestions must contain [placeholder] syntax without inventing facts
        for s in p["wording_suggestions"]:
            self.assertIn("[", s["suggestion"])
            self.assertIn("]", s["suggestion"])

        for t in result["sample_templates"]:
            self.assertIn("[", t["template"])
            self.assertIn("]", t["template"])

    def test_original_resume_text_remains_unchanged(self):
        original_text = "PROJECTS\nProject A | Python\nDeveloped an app to solve scheduling conflicts."
        copied_text = str(original_text)
        sections = {"projects": copied_text}
        check_project_descriptions(copied_text, resume_sections=sections)
        self.assertEqual(copied_text, original_text)
        self.assertEqual(sections["projects"], original_text)


    def test_numbered_projects(self):
        text = """
        PROJECTS
        1. Smart Inventory Manager
        Developed a desktop app using Python and SQLite to track retail warehouse inventory.
        Implemented automated alerts and bar-code scanning features.

        2. Task Automation Bot
        Created a Discord bot using Node.js to schedule team meetings and send reminders.
        Designed custom commands and handled WebSocket events.
        """
        result = check_project_descriptions(text)
        self.assertEqual(result["total_projects"], 2)
        self.assertIn("Smart Inventory Manager", result["projects"][0]["title"])
        self.assertIn("Task Automation Bot", result["projects"][1]["title"])

    def test_none_input(self):
        result = check_project_descriptions(None)
        self.assertEqual(result["total_projects"], 0)
        self.assertEqual(result["overall_status"], "No Content")


    def test_flask_integration_with_projects(self):
        from unittest.mock import patch
        import io
        from app import app

        test_client = app.test_client()
        resume_content = """
        John Doe
        john@example.com

        PROJECTS
        AI Resume Analyzer | Python, Flask
        Developed a web application designed to evaluate candidate resumes against ATS standards.
        Implemented REST APIs and optimized parsing algorithms, improving speed by 35%.
        """
        data = {
            "resume": (io.BytesIO(b"%PDF-1.4 test"), "test_resume.pdf"),
        }

        with patch("app.extract_resume_text", return_value=resume_content):
            response = test_client.post("/analyze", data=data, content_type="multipart/form-data")
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Project Description Quality", response.data)
            self.assertIn(b"AI Resume Analyzer", response.data)


if __name__ == "__main__":
    unittest.main()

