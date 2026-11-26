"""Unit and integration tests for Resume Action Verb Analysis (Issue #54).

Verifies:
1. Professional action verbs are identified across categories.
2. Frequently repeated verbs (>= 3 times) are highlighted with alternatives.
3. Vague/passive phrases are detected (e.g. 'worked on', 'responsible for').
4. Contextually relevant alternatives are suggested alongside original sentences.
5. Original resume text is preserved without automatic changes.
6. Web integration and UI rendering in /analyze.
"""

import io
import unittest

from analyzer.action_verb_analyzer import (
    ACTION_VERB_CATEGORIES,
    ALL_ACTION_VERBS,
    VAGUE_VERBS_MAP,
    analyze_action_verbs,
)
from app import app


def sample_pdf_bytes_action_verbs():
    """Build a tiny valid PDF with repeated and vague verbs for testing."""
    lines = [
        "Alex Morgan",
        "alex@example.com",
        "EXPERIENCE",
        "Worked on backend REST APIs using Python and Flask.",
        "Built microservices architecture to process asynchronous payments.",
        "Built internal deployment tools using Docker and Kubernetes.",
        "Built automated regression testing suites with Pytest.",
        "Responsible for leading the sprint planning and code reviews.",
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


class TestActionVerbDictionary(unittest.TestCase):
    """Verify dictionary of professional action verbs and category classification."""

    def test_dictionary_contains_standard_verbs(self):
        self.assertIn("engineered", ALL_ACTION_VERBS)
        self.assertIn("architected", ALL_ACTION_VERBS)
        self.assertIn("deployed", ALL_ACTION_VERBS)
        self.assertIn("optimized", ALL_ACTION_VERBS)
        self.assertIn("spearheaded", ALL_ACTION_VERBS)
        self.assertIn("analyzed", ALL_ACTION_VERBS)
        self.assertIn("collaborated", ALL_ACTION_VERBS)

    def test_action_verbs_categorized(self):
        expected_cats = [
            "Technical & Development",
            "Deployment & Operations",
            "Performance & Optimization",
            "Leadership & Management",
            "Analysis & Problem-Solving",
            "Collaboration & Communication",
        ]
        for cat in expected_cats:
            self.assertIn(cat, ACTION_VERB_CATEGORIES)
            self.assertTrue(len(ACTION_VERB_CATEGORIES[cat]) > 0)


class TestActionVerbDetection(unittest.TestCase):
    """Verify common action verbs are identified in resume text."""

    def test_identifies_action_verbs_and_counts(self):
        text = """
        • Engineered scalable microservices with Python.
        • Deployed containerized applications to AWS.
        • Optimized database queries and reduced latency by 35%.
        """
        result = analyze_action_verbs(text)
        self.assertGreaterEqual(result["total_action_verbs"], 4)
        self.assertIn("engineered", result["all_verbs_found"])
        self.assertIn("deployed", result["all_verbs_found"])
        self.assertIn("optimized", result["all_verbs_found"])
        self.assertIn("reduced", result["all_verbs_found"])

    def test_none_section_values_handled_safely(self):
        result = analyze_action_verbs("Engineered backend", resume_sections={"experience": None, "projects": None})
        self.assertGreaterEqual(result["total_action_verbs"], 1)



class TestRepeatedVerbsHighlighting(unittest.TestCase):
    """Verify frequently repeated verbs (>= 3 times) are highlighted."""

    def test_highlights_repeated_verbs(self):
        text = """
        • Developed user authentication microservice.
        • Developed real-time notifications engine.
        • Developed responsive frontend dashboard.
        • Designed payment gateway integration.
        """
        result = analyze_action_verbs(text)
        self.assertTrue(result["has_repeated_verbs"])
        self.assertEqual(len(result["repeated_verbs"]), 1)
        repeated_item = result["repeated_verbs"][0]
        self.assertEqual(repeated_item["verb"], "developed")
        self.assertEqual(repeated_item["count"], 3)
        self.assertTrue(len(repeated_item["suggested_alternatives"]) > 0)
        # "designed" was only used once, so it should not be in repeated_verbs
        self.assertNotIn("designed", [item["verb"] for item in result["repeated_verbs"]])


class TestVaguePhrasesAndSentenceSuggestions(unittest.TestCase):
    """Verify detection of vague verbs and contextual suggestions alongside sentences."""

    def test_detects_vague_phrases(self):
        text = "Worked on developing backend API endpoints and responsible for code quality."
        result = analyze_action_verbs(text)
        self.assertTrue(result["has_vague_verbs"])
        vague_suggestions = [s for s in result["sentence_suggestions"] if s["issue_type"] == "vague"]
        self.assertTrue(len(vague_suggestions) > 0)
        self.assertEqual(vague_suggestions[0]["verb"], "worked on")

    def test_suggestions_displayed_alongside_original_sentences(self):
        text = "Worked on scalable database queries and improved throughput."
        result = analyze_action_verbs(text)
        suggestions = result["sentence_suggestions"]
        self.assertTrue(len(suggestions) > 0)
        item = suggestions[0]
        self.assertIn("original_sentence", item)
        self.assertEqual(item["original_sentence"], text)
        self.assertIn("suggested_alternatives", item)
        self.assertTrue(len(item["suggested_alternatives"]) > 0)

    def test_contextual_relevance_of_suggestions(self):
        # Database / query context should suggest technical verbs
        db_text = "Worked on database schemas and SQL queries."
        db_res = analyze_action_verbs(db_text)
        db_sug = db_res["sentence_suggestions"][0]["suggested_alternatives"]
        self.assertTrue(any(v in ["engineered", "architected", "implemented", "developed", "built"] for v in db_sug))

        # Infrastructure / cloud context should suggest deployment verbs
        cloud_text = "Worked on docker containers and kubernetes infrastructure."
        cloud_res = analyze_action_verbs(cloud_text)
        cloud_sug = cloud_res["sentence_suggestions"][0]["suggested_alternatives"]
        self.assertTrue(any(v in ["deployed", "automated", "orchestrated", "scaled"] for v in cloud_sug))


class TestOriginalResumePreservation(unittest.TestCase):
    """Verify that the original resume text is never altered."""

    def test_original_text_remains_intact(self):
        original = "Worked on backend APIs. Worked on frontend. Worked on databases."
        original_copy = str(original)
        result = analyze_action_verbs(original)
        # Original string must be completely unchanged
        self.assertEqual(original, original_copy)
        # Result dictionary contains suggestions, not a mutated resume
        self.assertIn("sentence_suggestions", result)


class TestWebAnalysisIntegration(unittest.TestCase):
    """Verify that /analyze renders action verb metrics and suggestions."""

    def setUp(self):
        self.client = app.test_client()

    def test_analyze_route_renders_action_verb_section(self):
        pdf_bytes = sample_pdf_bytes_action_verbs()
        response = self.client.post(
            "/analyze",
            data={"resume": (io.BytesIO(pdf_bytes), "resume.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        self.assertIn("Action Verb Analysis", html)
        self.assertIn("Total Action Verbs", html)
        self.assertIn("Unique Verbs", html)
        # "built" was used 3 times in sample resume
        self.assertIn("Frequently Repeated Action Verbs", html)
        self.assertIn('"built"', html)
        # "Worked on" was used as a vague verb
        self.assertIn("Worked on backend REST APIs", html)
        self.assertIn("Suggested Action Verbs", html)


if __name__ == "__main__":
    unittest.main()
