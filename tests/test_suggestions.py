"""Tests for analyzer/suggestions.py

Run them from the project folder with:
    python -m unittest discover -s tests -v
"""

import unittest

from analyzer.suggestions import generate_recommendations

GOOD_RESUME = """Aarav Sharma
aarav@example.com | +91 98765 43210 | github.com/aarav-demo
Professional Summary
Final-year engineering student with hands-on experience building web apps using Python and Flask. Looking for a backend developer role.
Skills
Python, Flask, SQL, Git, HTML, CSS
Education
B.Tech in Electronics and Communication Engineering, Example College, 2023 - 2027
Experience
Web Development Intern, Example Pvt Ltd
- Built REST APIs that cut page load time by 30%
Projects
Campus Food App - ordering app built with React, Flask and SQL
""" + "extra words " * 60


def sections_of(text):
    return [block["section"] for block in generate_recommendations(text)]


def all_tips(text):
    return [item for block in generate_recommendations(text) for item in block["tips"]]


class RecommendationTests(unittest.TestCase):

    def test_complete_resume_has_no_missing_section_advice(self):
        names = sections_of(GOOD_RESUME)
        for section in ("Contact", "Summary", "Skills", "Education", "Projects"):
            self.assertNotIn(section, names)

    def test_missing_sections_are_reported(self):
        names = sections_of("Aarav Sharma\nSome text only")
        for section in ("Contact", "Summary", "Skills", "Education", "Experience", "Projects"):
            self.assertIn(section, names)

    def test_missing_contact_details(self):
        text = " ".join(item["tip"] for item in all_tips("Aarav\nSkills\nPython"))
        self.assertIn("email", text.lower())
        self.assertIn("phone", text.lower())

    def test_none_or_empty_text_does_not_crash(self):
        self.assertIsInstance(generate_recommendations(None), list)
        self.assertIsInstance(generate_recommendations(""), list)


    def test_weak_phrase_is_rewritten_with_the_users_own_words(self):
        resume = GOOD_RESUME.replace(
            "- Built REST APIs that cut page load time by 30%",
            "- Worked on the login page for students",
        )
        examples = [item["example"] for item in all_tips(resume)]
        self.assertIn("[Action verb] the login page for students", examples)

    def test_experience_without_numbers(self):
        resume = GOOD_RESUME.replace(" by 30%", "")
        text = " ".join(item["tip"] for item in all_tips(resume))
        self.assertIn("No numbers found", text)

    def test_projects_without_technologies(self):
        resume = GOOD_RESUME.replace(
            "Campus Food App - ordering app built with React, Flask and SQL",
            "Campus Food App - an ordering app for students",
        )
        text = " ".join(item["tip"] for item in all_tips(resume))
        self.assertIn("do not mention any technologies", text)

    def test_nothing_is_made_up(self):
        # A resume with no Docker, Java or AWS must never get advice that names them,
        # and every example must be a template with [placeholders].
        resume = "Aarav\nSkills\nPython\nProjects\nWorked on a website"
        for item in all_tips(resume):
            for invented in ("Docker", "Java", "AWS", "Google", "Microsoft"):
                self.assertNotIn(invented, item["tip"] + item["example"])
            if item["example"]:
                self.assertIn("[", item["example"])

    def test_empty_text_does_not_crash(self):
        self.assertTrue(generate_recommendations(""))


if __name__ == "__main__":
    unittest.main()