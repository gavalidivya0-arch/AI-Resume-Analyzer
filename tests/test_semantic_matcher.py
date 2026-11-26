import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from analyzer.semantic_matcher import (
    compute_cosine_similarity,
    generate_embedding,
    calculate_text_similarity,
    calculate_section_similarities,
    identify_semantically_related_skills,
    calculate_semantic_job_match,
    get_embedding_model,
    set_embedding_model,
    reset_embedding_model,
)
from analyzer.job_matcher import (
    match_resume_to_job,
    HIRING_DISCLAIMER,
)


class TestSemanticMatcher(unittest.TestCase):

    def test_compute_cosine_similarity_identical_vectors(self):
        v = np.array([1.0, 2.0, 3.0])
        sim = compute_cosine_similarity(v, v)
        self.assertAlmostEqual(sim, 1.0, places=4)

    def test_compute_cosine_similarity_orthogonal_vectors(self):
        v1 = np.array([1.0, 0.0])
        v2 = np.array([0.0, 1.0])
        sim = compute_cosine_similarity(v1, v2)
        self.assertAlmostEqual(sim, 0.0, places=4)

    def test_compute_cosine_similarity_zero_vector(self):
        v1 = np.array([0.0, 0.0])
        v2 = np.array([1.0, 2.0])
        sim = compute_cosine_similarity(v1, v2)
        self.assertEqual(sim, 0.0)

    def test_compute_cosine_similarity_none_vectors(self):
        self.assertEqual(compute_cosine_similarity(None, np.array([1.0])), 0.0)
        self.assertEqual(compute_cosine_similarity(np.array([1.0]), None), 0.0)

    def test_empty_or_whitespace_text_handling(self):
        self.assertEqual(calculate_text_similarity("", "job description"), 0.0)
        self.assertEqual(calculate_text_similarity("resume text", "   "), 0.0)
        self.assertEqual(calculate_text_similarity(None, None), 0.0)
        self.assertIsNone(generate_embedding(""))
        self.assertIsNone(generate_embedding(None))

    def test_identify_semantically_related_terms(self):
        """Acceptance Criteria 1: Semantically related terms can be identified."""
        unmatched_skills = ["Machine Learning", "Kubernetes"]
        candidate_skills = ["Deep Learning", "Docker", "Cooking"]

        related = identify_semantically_related_skills(
            unmatched_skills=unmatched_skills,
            candidate_skills=candidate_skills,
            threshold=0.60,
        )

        # Machine Learning and Deep Learning should be identified as semantically related
        matched_reqs = {r["required_skill"] for r in related}
        self.assertIn("Machine Learning", matched_reqs)

        ml_entry = next(r for r in related if r["required_skill"] == "Machine Learning")
        self.assertEqual(ml_entry["matched_skill"], "Deep Learning")
        self.assertGreaterEqual(ml_entry["similarity"], 60)

    def test_unrelated_terms_not_matched(self):
        unmatched_skills = ["Machine Learning"]
        candidate_skills = ["Baking", "Carpentry"]

        related = identify_semantically_related_skills(
            unmatched_skills=unmatched_skills,
            candidate_skills=candidate_skills,
            threshold=0.60,
        )
        self.assertEqual(len(related), 0)

    def test_calculate_section_similarities(self):
        """Proposed solution: Calculate similarity between relevant sections."""
        resume_sections = {
            "skills": "Python, Machine Learning, PyTorch, SQL, Pandas",
            "experience": "Developed scalable NLP microservices and deep learning pipelines.",
            "projects": "Built an AI-powered resume parsing application.",
            "summary": "Experienced Data Scientist specializing in AI and distributed systems.",
            "education": "B.S. in Computer Science",
        }
        jd = "Looking for a Machine Learning Engineer with experience in Python and NLP."

        section_sims = calculate_section_similarities(resume_sections, jd)
        self.assertIsInstance(section_sims, dict)
        self.assertIn("Skills", section_sims)
        self.assertIn("Work Experience", section_sims)
        self.assertIn("Projects", section_sims)
        self.assertIn("Professional Summary", section_sims)
        # Non-empty relevant sections should have positive percentage scores
        for name, score in section_sims.items():
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 100)

    def test_combined_semantic_and_keyword_matching(self):
        """Proposed solution: Combine semantic similarity with keyword matching."""
        resume_skills = ["Python", "Flask"]
        resume_text = (
            "Senior Backend Engineer with 5 years experience building Python web services, "
            "REST APIs, and database-driven applications using Flask and SQL."
        )
        resume_sections = {
            "skills": "Python, Flask",
            "experience": "Built REST APIs and backend web services.",
        }
        jd = "Seeking a Backend Developer proficient in Python, Flask, Docker, and REST API."

        result = match_resume_to_job(
            resume_skills=resume_skills,
            job_description=jd,
            resume_text=resume_text,
            resume_sections=resume_sections,
        )

        self.assertTrue(result["has_job_description"])
        self.assertIn("Python", result["matching_skills"])
        self.assertIn("Flask", result["matching_skills"])
        self.assertIsNotNone(result["semantic_match_percentage"])
        self.assertGreater(result["semantic_match_percentage"], 0)
        self.assertEqual(result["keyword_match_percentage"], 50)  # 2 of 4 (Python, Flask, Docker, REST API)

        # Combined match percentage is the average of keyword and semantic similarity
        expected_combined = round(0.5 * result["keyword_match_percentage"] + 0.5 * result["semantic_match_percentage"])
        self.assertEqual(result["match_percentage"], expected_combined)

    def test_understandable_explanation(self):
        """Acceptance Criteria 2: Matching results include an understandable explanation."""
        resume_skills = ["Python", "Deep Learning"]
        resume_text = "Experienced in Python and Deep Learning model development."
        jd = "Requirements: Python, Machine Learning, AWS"

        result = match_resume_to_job(
            resume_skills=resume_skills,
            job_description=jd,
            resume_text=resume_text,
        )

        explanation = result["explanation"]
        self.assertIn("Overall match score", explanation)
        self.assertIn("combines keyword matching", explanation)
        self.assertIn("semantic content similarity", explanation)
        # Should explain direct matches
        self.assertIn("required skills were exact matches", explanation)

    def test_similarity_scores_not_presented_as_hiring_guarantees(self):
        """Acceptance Criteria 4: Similarity scores are not presented as guaranteed hiring probabilities."""
        resume_skills = ["Python"]
        jd = "Requirements: Python, SQL"

        result = match_resume_to_job(resume_skills, jd, resume_text="Python developer")

        # Must have explicit disclaimer field
        self.assertIn("disclaimer", result)
        self.assertIn("does not represent guaranteed hiring probability", result["disclaimer"])
        # Explanation must also include the non-guarantee notice
        self.assertIn("does not represent guaranteed hiring probability", result["explanation"])

    def test_model_errors_handled_gracefully_during_loading(self):
        """Acceptance Criteria 3: Model errors are handled gracefully."""
        # Mock get_embedding_model to simulate a complete model failure/missing model
        with patch("analyzer.semantic_matcher.get_embedding_model", return_value=None):
            result = match_resume_to_job(
                resume_skills=["Python"],
                job_description="Requirements: Python, Docker",
                resume_text="Python programmer",
            )

            # System must NOT crash; must fall back to keyword-only matching cleanly
            self.assertTrue(result["has_job_description"])
            self.assertEqual(result["matching_skills"], ["Python"])
            self.assertEqual(result["missing_skills"], ["Docker"])
            self.assertEqual(result["keyword_match_percentage"], 50)
            self.assertEqual(result["match_percentage"], 50)
            self.assertIsNone(result["semantic_match_percentage"])
            self.assertIn("disclaimer", result)

    def test_model_encoding_exception_handled_gracefully(self):
        """Acceptance Criteria 3: Runtime encoding errors are handled gracefully."""
        mock_model = MagicMock()
        mock_model.encode.side_effect = RuntimeError("CUDA out of memory or tensor dimension mismatch")

        with patch("analyzer.semantic_matcher.get_embedding_model", return_value=mock_model):
            result = match_resume_to_job(
                resume_skills=["Python", "SQL"],
                job_description="Requirements: Python, SQL, Docker",
                resume_text="Python and SQL developer",
            )

            # System must handle the exception gracefully without raising
            self.assertTrue(result["has_job_description"])
            self.assertEqual(set(result["matching_skills"]), {"Python", "SQL"})
            self.assertEqual(result["missing_skills"], ["Docker"])
            self.assertEqual(result["keyword_match_percentage"], 67)
            self.assertEqual(result["match_percentage"], 67)
            self.assertIn("disclaimer", result)


if __name__ == "__main__":
    unittest.main()
