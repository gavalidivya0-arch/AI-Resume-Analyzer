"""Tests for Pluggable NLP Model Architecture (Issue #37).

Acceptance criteria tested:
- Different NLP implementations can be configured (SentenceTransformer, TFIDF, Fallback).
- Model-specific code is separated from Flask routes.
- Missing model dependencies do not crash the basic application.
- Existing analysis functionality remains available across all providers.
"""

import io
import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from analyzer.nlp.base import BaseNLPModel
from analyzer.nlp.fallback_model import FallbackNLPModel
from analyzer.nlp.registry import (
    get_nlp_model,
    list_registered_models,
    register_nlp_model,
    reset_active_nlp_model,
    set_active_nlp_model,
)
from analyzer.nlp.tfidf_model import TFIDFModel
from analyzer.nlp.transformer_model import SentenceTransformerModel
from analyzer.semantic_matcher import (
    calculate_section_similarities,
    calculate_semantic_job_match,
    calculate_text_similarity,
    generate_embedding,
    identify_semantically_related_skills,
)
from app import app


class TestPluggableNLPArchitecture(unittest.TestCase):

    def setUp(self):
        reset_active_nlp_model()

    def tearDown(self):
        reset_active_nlp_model()

    def test_registered_models_available(self):
        """Acceptance Criteria 1: Multiple configurable NLP implementations exist."""
        registered = list_registered_models()
        self.assertIn("sentence_transformers", registered)
        self.assertIn("tfidf", registered)
        self.assertIn("fallback", registered)

    def test_custom_nlp_model_registration(self):
        """Acceptance Criteria 1: Custom NLP implementations can be registered."""
        class DummyCustomNLP(BaseNLPModel):
            @property
            def name(self) -> str:
                return "custom_dummy"

            def is_available(self) -> bool:
                return True

            def generate_embedding(self, text):
                return np.ones(10, dtype=np.float32)

            def compute_similarity(self, text1, text2):
                return 0.99

        register_nlp_model("custom_dummy", lambda: DummyCustomNLP())
        model = get_nlp_model("custom_dummy")
        self.assertIsInstance(model, DummyCustomNLP)
        self.assertEqual(model.compute_similarity("a", "b"), 0.99)

    def test_fallback_model_computes_similarity_and_embeddings(self):
        """Acceptance Criteria 4: Pure-Python fallback model produces valid metrics."""
        fallback = FallbackNLPModel()
        self.assertTrue(fallback.is_available())

        # Identical texts
        sim_identical = fallback.compute_similarity(
            "Experienced Python developer with Flask experience",
            "Experienced Python developer with Flask experience",
        )
        self.assertAlmostEqual(sim_identical, 1.0, places=3)

        # Related texts sharing vocabulary
        sim_related = fallback.compute_similarity(
            "Python backend developer with SQL and Docker",
            "Looking for Python engineer who knows Docker and SQL",
        )
        self.assertGreater(sim_related, 0.4)

        # Disjoint texts
        sim_disjoint = fallback.compute_similarity(
            "Baker and pastry chef with artisan bread expertise",
            "Kubernetes cluster administrator on AWS cloud",
        )
        self.assertEqual(sim_disjoint, 0.0)

        # Embedding generation
        emb = fallback.generate_embedding("Python Flask engineer")
        self.assertIsNotNone(emb)
        self.assertAlmostEqual(np.linalg.norm(emb), 1.0, places=3)

    def test_tfidf_model_computes_similarity_and_embeddings(self):
        """Acceptance Criteria 1 & 4: TF-IDF model operates without deep learning frameworks."""
        tfidf = TFIDFModel()
        self.assertTrue(tfidf.is_available())

        sim_identical = tfidf.compute_similarity("Docker containerization", "Docker containerization")
        self.assertAlmostEqual(sim_identical, 1.0, places=3)

        sim_overlap = tfidf.compute_similarity(
            "Senior Python developer building web APIs",
            "Python developer specialized in APIs",
        )
        self.assertGreater(sim_overlap, 0.3)

        emb = tfidf.generate_embedding("Machine Learning and Deep Learning")
        self.assertIsNotNone(emb)
        self.assertAlmostEqual(np.linalg.norm(emb), 1.0, places=3)

    def test_sentence_transformer_model_wrapper(self):
        """SentenceTransformerModel properly encapsulates model loading and inference."""
        mock_instance = MagicMock()
        mock_instance.encode.return_value = np.array([1.0, 0.0, 0.0], dtype=np.float32)

        st_model = SentenceTransformerModel(model_instance=mock_instance)
        self.assertTrue(st_model.is_available())
        self.assertEqual(st_model.name, "sentence_transformers")

        emb = st_model.generate_embedding("Cloud Engineer")
        self.assertIsNotNone(emb)
        self.assertEqual(len(emb), 3)

        mock_instance.encode.side_effect = [
            np.array([1.0, 0.0, 0.0], dtype=np.float32),
            np.array([1.0, 0.0, 0.0], dtype=np.float32),
        ]
        sim = st_model.compute_similarity("Cloud Engineer", "Cloud Engineer")
        self.assertAlmostEqual(sim, 1.0, places=3)

    def test_missing_model_dependencies_graceful_fallback(self):
        """Acceptance Criteria 3: Missing dependencies fall back without crashing."""
        # Simulate SentenceTransformer being unavailable (e.g. missing torch/package)
        with patch("analyzer.nlp.transformer_model.SentenceTransformerModel._ensure_loaded", return_value=False):
            # Requesting sentence_transformers should automatically fallback to tfidf or fallback
            model = get_nlp_model("sentence_transformers", fallback_on_unavailable=True)
            self.assertIsNotNone(model)
            self.assertIn(model.name, ["tfidf", "fallback"])
            self.assertTrue(model.is_available())

            # Similarity still calculates cleanly
            sim = model.compute_similarity("Python developer", "Python engineer")
            self.assertGreaterEqual(sim, 0.0)
            self.assertLessEqual(sim, 1.0)

    def test_switching_nlp_model_at_runtime(self):
        """Acceptance Criteria 1: Dynamic configuration of active NLP model."""
        set_active_nlp_model("tfidf")
        active = get_nlp_model()
        self.assertEqual(active.name, "tfidf")

        set_active_nlp_model("fallback")
        active = get_nlp_model()
        self.assertEqual(active.name, "fallback")

    def test_analysis_pipeline_with_tfidf_provider(self):
        """Acceptance Criteria 4: Existing analysis works end-to-end with alternative NLP provider."""
        set_active_nlp_model("tfidf")

        resume_sections = {
            "skills": "Python, SQL, Docker",
            "experience": "Developed web applications with Python and SQL",
        }
        jd = "Looking for Python and SQL developer"

        # 1. calculate_section_similarities
        sec_sims = calculate_section_similarities(resume_sections, jd)
        self.assertIsInstance(sec_sims, dict)
        self.assertIn("Skills", sec_sims)
        self.assertIn("Work Experience", sec_sims)

        # 2. calculate_semantic_job_match
        match_result = calculate_semantic_job_match(
            resume_text="Python and SQL developer",
            job_description=jd,
            resume_sections=resume_sections,
            resume_skills=["Python", "SQL"],
            missing_skills=["Docker"],
        )
        self.assertEqual(match_result["status"], "available")
        self.assertIsNotNone(match_result["semantic_similarity"])
        self.assertGreater(match_result["semantic_similarity"], 0)

    def test_analysis_pipeline_with_fallback_provider(self):
        """Acceptance Criteria 4: Existing analysis works end-to-end with fallback provider."""
        set_active_nlp_model("fallback")

        sim = calculate_text_similarity(
            "Experienced Python and Django backend developer",
            "Seeking Python and Django engineer for backend API development",
        )
        self.assertIsNotNone(sim)
        self.assertGreater(sim, 0.3)

    def test_flask_app_routes_do_not_crash_when_transformer_missing(self):
        """Acceptance Criteria 2 & 3: Flask routes remain decoupled and functional when deep learning model is absent."""
        client = app.test_client()

        # Simulate SentenceTransformer being unavailable
        with patch("analyzer.nlp.transformer_model.SentenceTransformerModel._ensure_loaded", return_value=False):
            # Activate fallback provider
            set_active_nlp_model("fallback")

            # Fake minimal PDF content
            pdf_bytes = (
                b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
                b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
                b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] >>\nendobj\n"
                b"xref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000115 00000 n \n"
                b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n185\n%%EOF\n"
            )

            with patch("app.extract_resume_text", return_value="Jane Doe\nSkills: Python, SQL\nExperience: Built APIs"):
                response = client.post(
                    "/analyze",
                    data={
                        "resume": (io.BytesIO(pdf_bytes), "resume.pdf"),
                        "job_description": "We need a Python developer who knows SQL.",
                    },
                    content_type="multipart/form-data",
                )

            # Application returns 200 OK without crashing
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)
            self.assertIn("Your Resume Analysis", html)
            self.assertIn("Python", html)


if __name__ == "__main__":
    unittest.main()
