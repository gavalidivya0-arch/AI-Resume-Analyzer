import io
import os
import re
import tempfile
import unittest
from unittest.mock import patch

from analyzer.resume_scorer import calculate_resume_score
from app import app

CSS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "static",
    "style.css",
)

# Same category names that result.html uses for the score breakdown.
BREAKDOWN = {
    "Contact Information": 10,
    "Professional Summary": 0,
    "Technical Skills": 4,
    "Education": 15,
    "Experience": 0,
    "Projects": 0,
    "Readability": 5,
}

SAMPLE_RESUME = """Jane Doe
jane@example.com | +91 98765 43210
PROFESSIONAL SUMMARY
Backend developer who likes building reliable web applications.
SKILLS
Python, Flask, SQL, Git
EXPERIENCE
Software intern, Acme Corp
EDUCATION
B.Tech Computer Science, Example University
PROJECTS
Resume analyzer built with Flask
"""


class ScoreRingTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.original_upload_folder = app.config["UPLOAD_FOLDER"]
        cls.upload_directory = tempfile.TemporaryDirectory()
        app.config["UPLOAD_FOLDER"] = cls.upload_directory.name

    @classmethod
    def tearDownClass(cls):
        app.config["UPLOAD_FOLDER"] = cls.original_upload_folder
        cls.upload_directory.cleanup()

    def setUp(self):
        self.client = app.test_client()

    def upload(self):
        response = self.client.post(
            "/analyze",
            data={"resume": (io.BytesIO(b"%PDF-1.7"), "resume.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def page_for_score(self, score):
        """Render the results page when the backend returns this score."""
        score_data = {
            "score": score,
            "breakdown": BREAKDOWN,
            "detected_skills": [],
            "word_count": 120,
        }

        with patch("app.extract_resume_text", return_value=SAMPLE_RESUME), \
                patch("app.calculate_resume_score", return_value=score_data):
            return self.upload()

    @staticmethod
    def read_ring(html):
        """Return what the page shows: number, aria value, ring offset."""
        number = re.search(
            r'class="score-ring-text">\s*<strong>(.*?)</strong>', html, re.S
        )
        aria = re.search(r'aria-valuenow="(.*?)"', html)
        offset = re.search(
            r'class="score-ring-fill"[^>]*?stroke-dashoffset="(.*?)"',
            html,
            re.S,
        )
        return {
            "number": number.group(1) if number else None,
            "aria": aria.group(1) if aria else None,
            "offset": offset.group(1) if offset else None,
            "has_fill": 'class="score-ring-fill"' in html,
        }

    def test_ring_matches_the_backend_score(self):
        for score in [1, 20, 58, 72, 99, 100]:
            with self.subTest(score=score):
                ring = self.read_ring(self.page_for_score(score))

                self.assertEqual(ring["number"], str(score))
                self.assertEqual(ring["aria"], str(score))
                # The ring is 100 long, so the empty part is 100 - score.
                self.assertEqual(ring["offset"], str(100 - score))

    def test_score_zero_shows_an_empty_ring(self):
        ring = self.read_ring(self.page_for_score(0))

        self.assertEqual(ring["number"], "0")
        self.assertEqual(ring["aria"], "0")
        self.assertFalse(ring["has_fill"])

    def test_full_score_fills_the_whole_ring(self):
        ring = self.read_ring(self.page_for_score(100))

        self.assertEqual(ring["offset"], "0")

    def test_out_of_range_scores_are_kept_between_0_and_100(self):
        too_high = self.read_ring(self.page_for_score(150))
        self.assertEqual(too_high["number"], "100")
        self.assertEqual(too_high["offset"], "0")

        too_low = self.read_ring(self.page_for_score(-5))
        self.assertEqual(too_low["number"], "0")
        self.assertFalse(too_low["has_fill"])

    def test_missing_score_does_not_break_the_page(self):
        ring = self.read_ring(self.page_for_score(None))

        self.assertEqual(ring["number"], "0")
        self.assertFalse(ring["has_fill"])

    def test_ring_is_a_labelled_progress_bar(self):
        html = self.page_for_score(58)

        self.assertIn('role="progressbar"', html)
        self.assertIn('aria-valuemin="0"', html)
        self.assertIn('aria-valuemax="100"', html)
        self.assertIn('aria-valuetext="58 out of 100"', html)

    def test_label_follows_the_score_bands(self):
        expected = {
            100: "Excellent Resume!", 80: "Excellent Resume!",
            79: "Good Progress!", 60: "Good Progress!",
            59: "Needs Improvement", 40: "Needs Improvement",
            39: "Keep Improving!", 0: "Keep Improving!",
        }

        for score, label in expected.items():
            with self.subTest(score=score):
                self.assertIn(label, self.page_for_score(score))

    def test_page_shows_the_real_score_of_the_resume(self):
        real_score = calculate_resume_score(SAMPLE_RESUME)["score"]

        with patch("app.extract_resume_text", return_value=SAMPLE_RESUME):
            ring = self.read_ring(self.upload())

        self.assertEqual(ring["number"], str(real_score))
        self.assertEqual(ring["aria"], str(real_score))
        self.assertEqual(ring["offset"], str(100 - real_score))

    def test_every_analysis_gets_its_own_ring(self):
        first = self.read_ring(self.page_for_score(72))
        second = self.read_ring(self.page_for_score(20))
        third = self.read_ring(self.page_for_score(72))

        self.assertEqual(first, third)
        self.assertNotEqual(first["number"], second["number"])
        self.assertNotEqual(first["offset"], second["offset"])

    def test_old_broken_circle_is_gone(self):
        html = self.page_for_score(58)

        self.assertNotIn("score-circle", html)
        self.assertNotIn("--score:", html)


class ScoreRingStyleTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(CSS_PATH, encoding="utf-8") as css_file:
            cls.css = css_file.read()

    def test_invalid_percentage_calculation_is_not_used(self):
        # calc(58% * 1%) is invalid CSS, so the old ring never appeared.
        self.assertNotIn("calc(var(--score)", self.css)

    def test_ring_colors_exist_for_both_themes(self):
        self.assertEqual(self.css.count("--ring-start:"), 2)
        self.assertEqual(self.css.count("--ring-end:"), 2)

        dark_block = self.css[self.css.index('[data-theme="dark"]'):]
        self.assertIn("--ring-start:", dark_block.split("}")[0])

    def test_ring_uses_theme_variables_not_fixed_colors(self):
        for rule in [".score-ring-track {", ".score-ring-stop-start {"]:
            body = self.css[self.css.index(rule):].split("}")[0]
            self.assertIn("var(--", body, rule)

    def test_animation_is_switched_off_for_reduced_motion(self):
        self.assertIn("@keyframes score-ring-grow", self.css)
        self.assertIn("prefers-reduced-motion: reduce", self.css)


if __name__ == "__main__":
    unittest.main()