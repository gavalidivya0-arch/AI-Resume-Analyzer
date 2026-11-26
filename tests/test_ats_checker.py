import unittest

from analyzer.ats_checker import analyze_ats, detect_sections

GOOD_RESUME = """
Priya Sharma
priya@example.com | +91 98765 43210 | github.com/priya

SUMMARY
Backend developer who enjoys building reliable web apps.

SKILLS
Python, Flask, SQL, Git, Docker, React, HTML, CSS

EXPERIENCE
Software Intern, Acme Corp  Jun 2024 - Aug 2024
• Built REST APIs with Flask, improving response time by 30%
• Designed a SQL schema serving 5000 users
• Implemented automated tests and deployed with Docker
• Optimized queries and reduced load by 25%
• Led a team of 3 interns

PROJECTS
Resume Analyzer
• Developed a PDF analysis tool using Python
- Created a clean UI with HTML and CSS

EDUCATION
B.Tech Computer Science, 2021 - 2025

CERTIFICATIONS
AWS Cloud Practitioner
""" * 2

SKILLS = ["Python", "Flask", "SQL", "Git", "Docker"]


class DetectSectionsTests(unittest.TestCase):

    def test_finds_common_headings(self):
        text = "EXPERIENCE\nfoo\nTechnical Skills:\nbar\nEducation"
        self.assertEqual(
            detect_sections(text), {"experience", "skills", "education"}
        )

    def test_long_sentences_are_not_headings(self):
        text = "I have a lot of experience building web applications daily"
        self.assertEqual(detect_sections(text), set())

    def test_none_input_does_not_crash(self):
        self.assertEqual(detect_sections(None), set())
        result = analyze_ats(None, found_skills=None)
        self.assertIsInstance(result, dict)
        self.assertIn("score", result)



class AnalyzeAtsTests(unittest.TestCase):

    def test_good_resume_scores_high(self):
        result = analyze_ats(GOOD_RESUME, SKILLS)
        self.assertGreaterEqual(result["score"], 70)
        self.assertEqual(result["missing_sections"], [])

    def test_empty_text_does_not_crash(self):
        result = analyze_ats("")
        self.assertLess(result["score"], 30)
        severities = [i["severity"] for i in result["formatting_issues"]]
        self.assertIn("high", severities)

    def test_missing_sections_are_reported(self):
        text = "Jane Doe jane@example.com\n" + "I like coding. " * 40
        result = analyze_ats(text, [])
        names = [m["name"] for m in result["missing_sections"]]
        self.assertIn("Education", names)
        self.assertIn("Skills", names)

    def test_recommendations_are_not_duplicated(self):
        result = analyze_ats("hello", [])
        recs = result["recommendations"]
        self.assertEqual(len(recs), len(set(recs)))

    def test_disclaimer_is_always_present_and_no_guarantee_claimed(self):
        result = analyze_ats(GOOD_RESUME, SKILLS)
        self.assertIn("does not guarantee", result["disclaimer"])

    def test_breakdown_max_is_100(self):
        result = analyze_ats(GOOD_RESUME, SKILLS)
        total_max = sum(item["max"] for item in result["breakdown"].values())
        self.assertEqual(total_max, 100)
        self.assertLessEqual(result["score"], 100)


if __name__ == "__main__":
    unittest.main()