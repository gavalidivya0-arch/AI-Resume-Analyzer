"""Unit tests for Semantic Duplicate Detection (Issue #35).

Acceptance criteria tested:
- Similar sentences are identified.
- Thresholds can be adjusted.
- Results distinguish exact duplicates from semantic similarity.
- Original resume content is never automatically deleted.
"""

import io
import unittest
from unittest.mock import MagicMock
import numpy as np
from fpdf import FPDF

from analyzer.duplicate_detector import (
    DEFAULT_EXACT_THRESHOLD,
    DEFAULT_SEMANTIC_THRESHOLD,
    detect_duplicates,
    extract_sentences_and_bullets,
    normalize_for_exact_match,
)
from app import app


class DuplicateDetectorUnitTests(unittest.TestCase):

    def test_extract_sentences_and_bullets(self):
        """Sentence extractor correctly parses bullet points and filters headings."""
        text = (
            "Alex Smith\n"
            "alex@example.com\n"
            "WORK EXPERIENCE\n"
            "• Developed scalable REST APIs using Flask and Docker.\n"
            "• Built automated CI/CD deployment pipelines on GitHub Actions.\n"
            "PROJECTS\n"
            "- Designed an AI Resume Analyzer processing PDF documents.\n"
            "SKILLS\n"
            "Python, SQL, Docker\n"
        )
        sentences = extract_sentences_and_bullets(text, min_words=4)
        self.assertEqual(len(sentences), 3)
        self.assertIn("Developed scalable REST APIs using Flask and Docker.", sentences)
        self.assertIn("Built automated CI/CD deployment pipelines on GitHub Actions.", sentences)
        self.assertIn("Designed an AI Resume Analyzer processing PDF documents.", sentences)
        # Section headers and contact info should not be treated as sentences
        self.assertNotIn("WORK EXPERIENCE", sentences)
        self.assertNotIn("PROJECTS", sentences)

    def test_results_distinguish_exact_duplicates_from_semantic_similarity(self):
        """Acceptance Criteria 3: Results distinguish exact duplicates from semantic similarity."""
        # 1 exact duplicate pair and 1 semantic pair
        s_exact_1 = "Led agile team meetings and coordinated weekly sprint planning sessions."
        s_exact_2 = "• Led agile team meetings and coordinated weekly sprint planning sessions."

        s_semantic_1 = "Engineered high-performance REST APIs with Flask and containerized them using Docker."
        s_semantic_2 = "Built scalable backend RESTful web services in Python Flask deployed with Docker."

        resume_text = f"{s_exact_1}\n{s_exact_2}\n{s_semantic_1}\n{s_semantic_2}\n"

        # Mock model to return controlled embeddings
        mock_model = MagicMock()
        # Mock encoding: semantic pair vectors close to each other
        vec_exact = np.array([1.0, 0.0, 0.0])
        vec_sem1 = np.array([0.0, 1.0, 0.0])
        vec_sem2 = np.array([0.0, 0.95, 0.31])  # Cosine similarity ~ 0.95

        def encode_mock(text, *args, **kwargs):
            if "agile" in text.lower():
                return vec_exact
            elif "flask" in text.lower() and "engineered" in text.lower():
                return vec_sem1
            elif "flask" in text.lower():
                return vec_sem2
            return np.array([0.5, 0.5, 0.5])

        mock_model.encode = MagicMock(side_effect=encode_mock)

        result = detect_duplicates(resume_text, semantic_threshold=0.80, model=mock_model)

        self.assertTrue(result["has_duplicates"])
        self.assertEqual(result["exact_duplicates_count"], 1)
        self.assertEqual(result["semantic_duplicates_count"], 1)
        self.assertEqual(result["total_duplicates_count"], 2)

        types = [p["type"] for p in result["duplicate_pairs"]]
        self.assertIn("exact", types)
        self.assertIn("semantic", types)

        exact_pair = next(p for p in result["duplicate_pairs"] if p["type"] == "exact")
        self.assertEqual(exact_pair["similarity_percentage"], 100)
        self.assertIn("identical wording", exact_pair["explanation"])

        semantic_pair = next(p for p in result["duplicate_pairs"] if p["type"] == "semantic")
        self.assertGreaterEqual(semantic_pair["similarity_percentage"], 80)
        self.assertIn("nearly identical information", semantic_pair["explanation"])

    def test_similar_sentences_are_identified_via_embeddings(self):
        """Acceptance Criteria 1: Similar sentences are identified."""
        s1 = "Designed and deployed microservices on AWS Elastic Kubernetes Service."
        s2 = "Architected scalable Kubernetes container clusters hosted on Amazon Web Services."

        resume_text = f"• {s1}\n• {s2}\n• Created frontend dashboards using React and Tailwind CSS."

        # Mock embeddings with cosine similarity ~ 0.88
        mock_model = MagicMock()
        v1 = np.array([1.0, 0.2, 0.0])
        v1 = v1 / np.linalg.norm(v1)
        v2 = np.array([0.9, 0.4, 0.0])
        v2 = v2 / np.linalg.norm(v2)
        v_react = np.array([0.0, 0.0, 1.0])

        def encode_side_effect(text, *args, **kwargs):
            if "kubernetes" in text.lower() and "designed" in text.lower():
                return v1
            elif "kubernetes" in text.lower():
                return v2
            return v_react

        mock_model.encode = MagicMock(side_effect=encode_side_effect)

        result = detect_duplicates(resume_text, semantic_threshold=0.80, model=mock_model)

        self.assertTrue(result["has_duplicates"])
        self.assertEqual(result["semantic_duplicates_count"], 1)
        pair = result["duplicate_pairs"][0]
        self.assertEqual(pair["type"], "semantic")
        self.assertIn("microservices on AWS", pair["sentence_1"])
        self.assertIn("Kubernetes container clusters", pair["sentence_2"])

    def test_thresholds_can_be_adjusted(self):
        """Acceptance Criteria 2: Thresholds can be adjusted to tune detection sensitivity."""
        s1 = "Built backend APIs using Python and PostgreSQL."
        s2 = "Developed server endpoints with Python and relational database."

        resume_text = f"• {s1}\n• {s2}\n"

        # Mock similarity = 0.82
        mock_model = MagicMock()
        v1 = np.array([1.0, 0.0])
        v2 = np.array([0.82, 0.5723])  # dot product = 0.82
        mock_model.encode = MagicMock(side_effect=lambda t, *args, **kwargs: v1 if "built" in t.lower() else v2)

        # 1. With semantic_threshold = 0.80 -> Detected as duplicate
        res_lenient = detect_duplicates(resume_text, semantic_threshold=0.80, model=mock_model)
        self.assertTrue(res_lenient["has_duplicates"])
        self.assertEqual(res_lenient["semantic_duplicates_count"], 1)

        # 2. With stricter threshold = 0.90 -> Not detected as duplicate
        res_strict = detect_duplicates(resume_text, semantic_threshold=0.90, model=mock_model)
        self.assertFalse(res_strict["has_duplicates"])
        self.assertEqual(res_strict["semantic_duplicates_count"], 0)

    def test_original_resume_content_is_never_automatically_deleted(self):
        """Acceptance Criteria 4: Original resume content is never automatically deleted."""
        raw_resume = (
            "Jane Doe\n"
            "jane@example.com\n"
            "• Managed MySQL database backups and data integrity.\n"
            "• Managed MySQL database backups and data integrity.\n"
            "• Implemented unit tests achieving 95 percent test coverage.\n"
        )

        result = detect_duplicates(raw_resume, semantic_threshold=0.80)

        # Content must not be deleted or modified
        self.assertTrue(result["original_text_preserved"])
        # Both duplicate lines still exist in input
        self.assertEqual(raw_resume.count("Managed MySQL database"), 2)


class AppDuplicateDetectionIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_upload_resume_with_duplicates_highlights_repetitive_content(self):
        """Uploading resume displays duplicate content analysis without deleting original text."""
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.cell(0, 10, "Alex Smith | alex@example.com", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 10, "Developed scalable REST APIs using Flask and Docker.", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 10, "Developed scalable REST APIs using Flask and Docker.", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 10, "Maintained unit testing with pytest.", new_x="LMARGIN", new_y="NEXT")

        pdf_bytes = io.BytesIO()
        pdf.output(pdf_bytes)
        pdf_bytes.seek(0)

        response = self.client.post(
            "/analyze",
            data={"resume": (pdf_bytes, "resume.pdf")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        # Verifies duplicate analysis section is rendered
        self.assertIn("Content Repetition & Duplicate Detection", html)
        self.assertIn("Exact Duplicate", html)
        self.assertIn("Safe Analysis", html)
        # Original text remains completely accessible and extracted
        self.assertIn("Extracted Resume Text", html)
        self.assertIn("Developed scalable REST APIs using Flask and Docker.", html)


if __name__ == "__main__":
    unittest.main()
