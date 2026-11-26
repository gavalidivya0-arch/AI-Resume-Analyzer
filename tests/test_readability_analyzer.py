"""Unit and integration tests for Resume Readability Analysis (Issue #55).

Verifies:
1. Average sentence length and readability metrics calculation.
2. Identification of unusually long sentences (> 25 words).
3. Detection of complex wording and polysyllabic word percentage.
4. Clear, actionable readability recommendations.
5. Safe handling of empty, brief, and varied resume inputs.
6. Web integration and UI rendering in /analyze.
"""

import io
import unittest

from analyzer.readability_analyzer import (
    analyze_readability,
    calculate_flesch_reading_ease,
    count_syllables,
    get_reading_level,
    is_complex_word,
    split_into_sentences,
)
from app import app


def sample_pdf_bytes():
    """Build a tiny valid PDF for integration tests."""
    lines = [
        "Jane Doe",
        "jane@example.com",
        "SKILLS",
        "Python, Docker, SQL",
        "EXPERIENCE",
        "Engineered scalable backend microservices using Python and Flask.",
        "Collaborated with cross-functional teams to deploy containerized APIs on AWS infrastructure.",
        "Spearheaded the comprehensive architectural redesign and end-to-end modernization of legacy monolithic enterprise infrastructure by orchestrating high-performance distributed microservices, implementing asynchronous message queues with RabbitMQ, and integrating real-time container monitoring dashboards that enhanced reliability.",
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


class TestSyllableAndWordComplexity(unittest.TestCase):
    """Verify syllable counting and complex word identification."""

    def test_count_syllables(self):
        cases = {
            "cat": 1,
            "code": 1,          # silent trailing e
            "built": 1,
            "python": 2,
            "table": 2,
            "engineer": 3,
            "development": 4,
            "implementation": 5,
        }
        for word, expected in cases.items():
            with self.subTest(word=word):
                self.assertEqual(count_syllables(word), expected)

    def test_is_complex_word(self):
        self.assertTrue(is_complex_word("development"))
        self.assertTrue(is_complex_word("microservices"))
        self.assertTrue(is_complex_word("orchestrating"))
        self.assertFalse(is_complex_word("code"))
        self.assertFalse(is_complex_word("fast"))
        self.assertFalse(is_complex_word("python"))


class TestSentenceSplitting(unittest.TestCase):
    """Verify resume text splitting into sentences and bullets."""

    def test_splits_sentences_and_bullets(self):
        text = """
        • Built backend microservices using Python and Flask.
        • Deployed Docker containers to Kubernetes clusters.
        Managed PostgreSQL databases with high availability.
        """
        sentences = split_into_sentences(text)
        self.assertEqual(len(sentences), 3)
        self.assertIn("Built backend microservices using Python and Flask.", sentences)
        self.assertIn("Deployed Docker containers to Kubernetes clusters.", sentences)
        self.assertIn("Managed PostgreSQL databases with high availability.", sentences)

    def test_abbreviations_do_not_cause_false_splits(self):
        text = "Led engineering projects e.g. cloud pipelines and microservices in U.S. data centers."
        sentences = split_into_sentences(text)
        self.assertEqual(len(sentences), 1)
        self.assertIn("e.g.", sentences[0])
        self.assertIn("U.S.", sentences[0])

    def test_ignores_section_headings(self):
        text = """
        EXPERIENCE
        • Built web application with React and Node.js.
        SKILLS
        Python, SQL, Docker
        """
        sentences = split_into_sentences(text)
        # Should not include "EXPERIENCE" or "SKILLS" as sentences
        self.assertNotIn("EXPERIENCE", sentences)
        self.assertNotIn("SKILLS", sentences)


class TestReadabilityMetrics(unittest.TestCase):
    """Verify calculation of readability scores and statistics."""

    def test_average_sentence_length(self):
        text = """
        Built backend API with Flask and Python.
        Deployed scalable microservices on AWS cloud.
        """
        result = analyze_readability(text)
        self.assertEqual(result["sentence_count"], 2)
        # 6 + 6 words = 12 words / 2 sentences = 6.0 avg
        self.assertGreater(result["word_count"], 0)
        self.assertAlmostEqual(result["avg_sentence_length"], 6.0, delta=1.0)

    def test_complex_word_detection(self):
        text = "Orchestrated comprehensive architectural modernization of distributed microservices."
        result = analyze_readability(text)
        self.assertGreater(result["complex_word_count"], 0)
        self.assertGreater(result["complex_word_percentage"], 30.0)
        self.assertTrue(any("architectural" in w.lower() or "modernization" in w.lower() for w in result["complex_words"]))

    def test_flesch_reading_ease_and_level(self):
        easy_score = calculate_flesch_reading_ease(total_words=100, total_sentences=10, total_syllables=130)
        self.assertGreater(easy_score, 60.0)
        self.assertEqual(get_reading_level(easy_score), "Balanced" if easy_score < 70 else "Easy to Skim")


class TestLongSentenceIdentification(unittest.TestCase):
    """Verify identification of unusually long sentences (> 25 words)."""

    def test_identifies_unusually_long_sentences(self):
        long_sent = (
            "Spearheaded the comprehensive architectural redesign and end-to-end "
            "modernization of legacy monolithic enterprise infrastructure by orchestrating "
            "high-performance distributed microservices, implementing asynchronous message "
            "queues with RabbitMQ, and integrating real-time container monitoring dashboards."
        )
        short_sent = "Built APIs using Python and Flask."
        text = f"{long_sent}\n{short_sent}"

        result = analyze_readability(text)
        self.assertEqual(result["long_sentence_count"], 1)
        self.assertEqual(len(result["long_sentences"]), 1)
        flagged = result["long_sentences"][0]
        self.assertGreaterEqual(flagged["word_count"], 25)
        self.assertIn("Spearheaded the comprehensive", flagged["sentence"])

    def test_short_sentences_not_flagged(self):
        text = """
        • Built web application with Flask.
        • Managed relational database instances.
        • Wrote automated unit tests with Pytest.
        """
        result = analyze_readability(text)
        self.assertEqual(result["long_sentence_count"], 0)
        self.assertEqual(result["long_sentences"], [])


class TestReadabilityRecommendations(unittest.TestCase):
    """Verify generation of clear, understandable recommendations."""

    def test_recommendations_for_long_sentences(self):
        long_sent = "A " * 30  # 30 words
        result = analyze_readability(long_sent)
        self.assertTrue(any("unusually long sentence" in rec.lower() for rec in result["recommendations"]))

    def test_positive_recommendation_for_balanced_resume(self):
        text = """
        • Engineered backend RESTful web services in Python and Flask.
        • Improved response times by forty percent across production endpoints.
        • Maintained continuous integration pipelines with GitHub Actions.
        """
        result = analyze_readability(text)
        self.assertTrue(len(result["recommendations"]) > 0)
        self.assertTrue(result["is_readable"])


class TestEdgeCasesAndSafety(unittest.TestCase):
    """Verify safe execution on empty or malformed inputs without exceptions."""

    def test_empty_string(self):
        result = analyze_readability("")
        self.assertEqual(result["word_count"], 0)
        self.assertEqual(result["sentence_count"], 0)
        self.assertEqual(result["avg_sentence_length"], 0.0)
        self.assertFalse(result["is_readable"])

    def test_none_input(self):
        result = analyze_readability(None)
        self.assertEqual(result["word_count"], 0)
        self.assertFalse(result["is_readable"])

    def test_whitespace_only(self):
        result = analyze_readability("    \n\t  ")
        self.assertEqual(result["word_count"], 0)
        self.assertFalse(result["is_readable"])


class TestWebAnalysisIntegration(unittest.TestCase):
    """Verify integration with Flask /analyze route."""

    def setUp(self):
        self.client = app.test_client()

    def test_analyze_route_renders_readability_section(self):
        pdf_bytes = sample_pdf_bytes()
        response = self.client.post(
            "/analyze",
            data={"resume": (io.BytesIO(pdf_bytes), "resume.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        self.assertIn("Resume Readability Analysis", html)
        self.assertIn("Avg Sentence Length", html)
        self.assertIn("Total Sentences", html)
        self.assertIn("Complex Word Usage", html)
        self.assertIn("Readability Recommendations", html)


if __name__ == "__main__":
    unittest.main()
