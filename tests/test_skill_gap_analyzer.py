"""Unit tests for Personalized Skill Gap Analysis (Issue #33).

Acceptance criteria tested:
- Skill gaps are identified for supported roles.
- Existing skills are not incorrectly marked as missing.
- Recommendations are relevant to the selected role.
- Users can understand why a skill is suggested.
"""

import io
import unittest
from fpdf import FPDF

from analyzer.skill_gap_analyzer import (
    ROLE_SKILL_REQUIREMENTS,
    analyze_skill_gap,
    get_best_matching_role,
    get_supported_roles,
    is_skill_present,
    normalize_skill,
    normalize_skill_set,
)
from app import app


class SkillGapAnalyzerTests(unittest.TestCase):

    def test_supported_roles_dataset_structure(self):
        """Acceptance Criteria 1: Structured skill requirement datasets for supported roles."""
        supported_roles = get_supported_roles()
        self.assertGreaterEqual(len(supported_roles), 7)
        self.assertIn("Backend Developer", supported_roles)
        self.assertIn("Frontend Developer", supported_roles)
        self.assertIn("Full Stack Developer", supported_roles)
        self.assertIn("Data Scientist", supported_roles)
        self.assertIn("Machine Learning Engineer", supported_roles)
        self.assertIn("DevOps Engineer", supported_roles)

        for role, requirements in ROLE_SKILL_REQUIREMENTS.items():
            self.assertGreater(len(requirements), 5, f"Role {role} has too few skills")
            for req in requirements:
                self.assertIn("skill", req)
                self.assertIn("category", req)
                self.assertIn("priority", req)
                self.assertIn("reason", req)
                self.assertIn("learning_tip", req)
                self.assertIn(req["priority"], ["High", "Medium", "Low"])
                # Understandable explanation check
                self.assertGreater(len(req["reason"]), 10)
                self.assertGreater(len(req["learning_tip"]), 10)

    def test_skill_gaps_are_identified_for_supported_roles(self):
        """Acceptance Criteria 1: Skill gaps are identified for supported roles."""
        # Candidate only has Python and Git
        candidate_skills = ["Python", "Git"]
        result = analyze_skill_gap(candidate_skills, target_role="Backend Developer")

        self.assertEqual(result["target_role"], "Backend Developer")
        self.assertFalse(result["is_auto_detected_role"])

        matching_names = [m["skill"] for m in result["matching_skills"]]
        missing_names = [m["skill"] for m in result["missing_skills"]]

        self.assertIn("Python", matching_names)
        self.assertIn("Git", matching_names)

        # Expected backend gaps
        self.assertIn("SQL", missing_names)
        self.assertIn("REST API", missing_names)
        self.assertIn("Docker", missing_names)
        self.assertGreater(result["total_missing"], 0)
        self.assertEqual(result["total_matching"], 2)

    def test_existing_skills_are_not_incorrectly_marked_as_missing(self):
        """Acceptance Criteria 2: Existing skills are not incorrectly marked as missing."""
        # Test case-insensitivity, aliases, and variations
        candidate_skills = [
            "python3",      # alias for Python
            "JS",           # alias for JavaScript
            "reactjs",      # alias for React
            "postgres",     # alias for PostgreSQL
            "k8s",          # alias for Kubernetes
            "HTML5",        # alias for HTML
            "CSS3",         # alias for CSS
            "RESTful API",  # alias for REST API
        ]

        result = analyze_skill_gap(candidate_skills, target_role="Full Stack Developer")
        missing_names = [m["skill"] for m in result["missing_skills"]]
        matching_names = [m["skill"] for m in result["matching_skills"]]

        # None of these possessed skills should be in missing_skills
        self.assertNotIn("Python", missing_names)
        self.assertNotIn("JavaScript", missing_names)
        self.assertNotIn("React", missing_names)
        self.assertNotIn("HTML", missing_names)
        self.assertNotIn("CSS", missing_names)
        self.assertNotIn("REST API", missing_names)

        # And they must be in matching_skills
        self.assertIn("Python", matching_names)
        self.assertIn("JavaScript", matching_names)
        self.assertIn("React", matching_names)
        self.assertIn("HTML", matching_names)
        self.assertIn("CSS", matching_names)
        self.assertIn("REST API", matching_names)

    def test_recommendations_are_relevant_to_the_selected_role(self):
        """Acceptance Criteria 3: Recommendations are relevant to the selected role."""
        # Candidate with minimal general skills
        candidate_skills = ["Git"]

        # Frontend evaluation
        frontend_res = analyze_skill_gap(candidate_skills, target_role="Frontend Developer")
        frontend_recommendations = [r["skill"] for r in frontend_res["learning_recommendations"]]
        self.assertIn("JavaScript", frontend_recommendations)
        self.assertIn("HTML", frontend_recommendations)
        self.assertIn("CSS", frontend_recommendations)
        self.assertIn("React", frontend_recommendations)
        # DevOps / Data skills should NOT be recommended for Frontend Developer
        self.assertNotIn("Kubernetes", frontend_recommendations)
        self.assertNotIn("Pandas", frontend_recommendations)

        # DevOps evaluation
        devops_res = analyze_skill_gap(candidate_skills, target_role="DevOps Engineer")
        devops_recommendations = [r["skill"] for r in devops_res["learning_recommendations"]]
        self.assertIn("Docker", devops_recommendations)
        self.assertIn("Kubernetes", devops_recommendations)
        self.assertIn("Linux", devops_recommendations)
        self.assertIn("CI/CD", devops_recommendations)
        self.assertNotIn("React", devops_recommendations)

    def test_users_can_understand_why_a_skill_is_suggested(self):
        """Acceptance Criteria 4: Users can understand why a skill is suggested."""
        candidate_skills = ["Python"]
        result = analyze_skill_gap(candidate_skills, target_role="Backend Developer")

        self.assertGreater(len(result["learning_recommendations"]), 0)
        for rec in result["learning_recommendations"]:
            # Must explain why it's suggested
            self.assertIn("reason", rec)
            self.assertIsInstance(rec["reason"], str)
            self.assertGreater(len(rec["reason"].strip()), 15)

            # Must provide actionable guidance
            self.assertIn("learning_tip", rec)
            self.assertIsInstance(rec["learning_tip"], str)
            self.assertGreater(len(rec["learning_tip"].strip()), 15)

    def test_prioritized_learning_recommendations_ordering(self):
        """Missing skills must be prioritized with High priority first, then Medium, then Low."""
        candidate_skills = []  # Missing everything
        result = analyze_skill_gap(candidate_skills, target_role="Backend Developer")

        priorities = [r["priority"] for r in result["learning_recommendations"]]
        # Ensure 'High' appears before 'Medium' and 'Medium' before 'Low'
        seen_medium = False
        seen_low = False
        for p in priorities:
            if p == "High":
                self.assertFalse(seen_medium, "High priority appeared after Medium")
                self.assertFalse(seen_low, "High priority appeared after Low")
            elif p == "Medium":
                seen_medium = True
                self.assertFalse(seen_low, "Medium priority appeared after Low")
            elif p == "Low":
                seen_low = True

    def test_best_matching_role_auto_detection(self):
        """When no target role is supplied, auto-detects the role with highest match."""
        ds_skills = ["Python", "SQL", "Pandas", "NumPy", "Scikit-Learn", "Machine Learning"]
        detected_role = get_best_matching_role(ds_skills)
        self.assertEqual(detected_role, "Data Scientist")

        result = analyze_skill_gap(ds_skills)
        self.assertEqual(result["target_role"], "Data Scientist")
        self.assertTrue(result["is_auto_detected_role"])
        self.assertGreaterEqual(result["match_percentage"], 60)

    def test_all_roles_summary_provides_comparative_view(self):
        """Summary contains comparative match score across all supported roles."""
        result = analyze_skill_gap(["Python", "Docker", "Linux"], target_role="DevOps Engineer")
        all_roles = result["all_roles_summary"]

        self.assertEqual(len(all_roles), len(get_supported_roles()))
        # Verify selected role is flagged
        selected_entries = [r for r in all_roles if r["is_selected"]]
        self.assertEqual(len(selected_entries), 1)
        self.assertEqual(selected_entries[0]["role"], "DevOps Engineer")


class AppSkillGapIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_home_page_contains_role_selector(self):
        """Home page must contain the target career role dropdown."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("target_role", html)
        self.assertIn("Backend Developer", html)
        self.assertIn("Frontend Developer", html)

    def test_upload_resume_with_selected_target_role(self):
        """Uploading resume with target_role renders personalized skill gap analysis."""
        # Simple one-page PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.cell(0, 10, "John Doe\njohn@example.com\nSkills: Python, Flask, SQL, Docker", new_x="LMARGIN", new_y="NEXT")

        pdf_bytes = io.BytesIO()
        pdf.output(pdf_bytes)
        pdf_bytes.seek(0)

        response = self.client.post(
            "/analyze",
            data={
                "resume": (pdf_bytes, "resume.pdf"),
                "target_role": "Backend Developer",
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        self.assertIn("Personalized Skill Gap Analysis", html)
        self.assertIn("Backend Developer", html)
        self.assertIn("Matching Skills", html)
        self.assertIn("Identified Skill Gaps", html)
        self.assertIn("Prioritized Learning Path", html)
        self.assertIn("Python", html)


if __name__ == "__main__":
    unittest.main()
