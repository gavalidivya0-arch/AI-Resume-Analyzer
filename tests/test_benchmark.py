"""Tests for Automated Resume Analysis Benchmarking (Issue #38).

Acceptance criteria tested:
- Benchmark tests run independently.
- Precision and recall are calculated correctly.
- Test documents do not contain real users' personal information.
- Results can be compared across code changes.
"""

import tempfile
import unittest

from benchmarks.dataset import SYNTHETIC_RESUMES, BenchmarkSample
from benchmarks.evaluator import (
    calculate_metrics,
    compare_benchmarks,
    evaluate_benchmark,
    format_benchmark_summary,
)
from benchmarks.run_benchmark import main


class TestBenchmarkMetrics(unittest.TestCase):

    def test_precision_recall_perfect_match(self):
        """Precision and recall should both be 1.0 when extracted matches expected exactly."""
        extracted = {"Python", "SQL", "Docker"}
        expected = {"Python", "SQL", "Docker"}

        metrics = calculate_metrics(extracted, expected)
        self.assertEqual(metrics["tp_count"], 3)
        self.assertEqual(metrics["fp_count"], 0)
        self.assertEqual(metrics["fn_count"], 0)
        self.assertEqual(metrics["precision"], 1.0)
        self.assertEqual(metrics["recall"], 1.0)
        self.assertEqual(metrics["f1_score"], 1.0)

    def test_precision_recall_partial_match(self):
        """Precision and recall are computed correctly for mixed predictions."""
        # TP = {"Python", "SQL"} (2)
        # FP = {"React", "AWS"} (2)
        # FN = {"Docker"} (1)
        extracted = {"Python", "SQL", "React", "AWS"}
        expected = {"Python", "SQL", "Docker"}

        metrics = calculate_metrics(extracted, expected)
        self.assertEqual(metrics["tp_count"], 2)
        self.assertEqual(metrics["fp_count"], 2)
        self.assertEqual(metrics["fn_count"], 1)

        # Precision = 2 / (2 + 2) = 0.50
        self.assertEqual(metrics["precision"], 0.50)
        # Recall = 2 / (2 + 1) = 0.6667
        self.assertAlmostEqual(metrics["recall"], 2 / 3, places=3)
        # F1 = 2 * (0.5 * 0.6667) / (0.5 + 0.6667) ~ 0.5714
        self.assertAlmostEqual(metrics["f1_score"], 0.5714, places=3)

    def test_precision_recall_zero_extracted(self):
        """When nothing is extracted but skills are expected, precision and recall are 0."""
        extracted = set()
        expected = {"Python", "SQL"}

        metrics = calculate_metrics(extracted, expected)
        self.assertEqual(metrics["tp_count"], 0)
        self.assertEqual(metrics["fp_count"], 0)
        self.assertEqual(metrics["fn_count"], 2)
        self.assertEqual(metrics["precision"], 0.0)
        self.assertEqual(metrics["recall"], 0.0)
        self.assertEqual(metrics["f1_score"], 0.0)

    def test_precision_recall_negative_control_empty_both(self):
        """Negative control: empty extracted and empty expected gives 1.0 precision and recall."""
        extracted = set()
        expected = set()

        metrics = calculate_metrics(extracted, expected)
        self.assertEqual(metrics["tp_count"], 0)
        self.assertEqual(metrics["fp_count"], 0)
        self.assertEqual(metrics["fn_count"], 0)
        self.assertEqual(metrics["precision"], 1.0)
        self.assertEqual(metrics["recall"], 1.0)
        self.assertEqual(metrics["f1_score"], 1.0)


class TestSyntheticDatasetSafety(unittest.TestCase):

    def test_synthetic_resumes_do_not_contain_real_pii(self):
        """Acceptance Criteria 3: Test documents do not contain real users' personal information."""
        self.assertGreater(len(SYNTHETIC_RESUMES), 0)

        for sample in SYNTHETIC_RESUMES:
            # Check ID is defined
            self.assertTrue(sample.sample_id)
            self.assertTrue(sample.role)

            # Check that any email address belongs strictly to the RFC 2606 example domain
            for line in sample.text.splitlines():
                if "@" in line:
                    self.assertIn(
                        "@example.com",
                        line.lower(),
                        f"Non-synthetic email detected in sample {sample.sample_id}: {line}",
                    )

            # Check that synthetic marker is present
            self.assertIn(
                "synthetic",
                sample.text.lower(),
                f"Sample {sample.sample_id} does not explicitly mark itself as synthetic.",
            )


class TestBenchmarkEvaluationAndComparison(unittest.TestCase):

    def test_evaluate_benchmark_end_to_end(self):
        """Acceptance Criteria 1: Benchmark runs independently and returns full metrics."""
        result = evaluate_benchmark()

        self.assertIn("samples_count", result)
        self.assertEqual(result["samples_count"], len(SYNTHETIC_RESUMES))
        self.assertIn("macro_metrics", result)
        self.assertIn("micro_metrics", result)

        macro = result["macro_metrics"]
        self.assertGreaterEqual(macro["precision"], 0.0)
        self.assertLessEqual(macro["precision"], 1.0)
        self.assertGreaterEqual(macro["recall"], 0.0)
        self.assertLessEqual(macro["recall"], 1.0)
        self.assertGreaterEqual(macro["f1_score"], 0.0)
        self.assertLessEqual(macro["f1_score"], 1.0)

        # High accuracy on built-in synthetic benchmark
        self.assertGreaterEqual(macro["f1_score"], 0.90)

    def test_format_benchmark_summary(self):
        """Benchmark summary generates readable formatted tables."""
        result = evaluate_benchmark()
        summary = format_benchmark_summary(result, verbose=True)

        self.assertIn("RESUME ANALYSIS ACCURACY BENCHMARK SUMMARY", summary)
        self.assertIn("Macro Precision", summary)
        self.assertIn("Macro Recall", summary)
        self.assertIn("Macro F1-Score", summary)
        self.assertIn("PER-SAMPLE BREAKDOWN", summary)

    def test_compare_benchmarks_tracks_improvements_and_regressions(self):
        """Acceptance Criteria 4: Results can be compared across code changes."""
        baseline = {
            "macro_metrics": {
                "precision": 0.85,
                "recall": 0.80,
                "f1_score": 0.8242,
            },
            "samples_count": 5,
        }

        # Case 1: Improvement
        improved_run = {
            "macro_metrics": {
                "precision": 0.90,
                "recall": 0.88,
                "f1_score": 0.8899,
            },
            "samples_count": 5,
        }
        diff_improved = compare_benchmarks(baseline, improved_run)
        self.assertTrue(diff_improved["improved"])
        self.assertFalse(diff_improved["regressed"])
        self.assertGreater(diff_improved["delta_f1"], 0)

        # Case 2: Regression
        regressed_run = {
            "macro_metrics": {
                "precision": 0.70,
                "recall": 0.75,
                "f1_score": 0.7241,
            },
            "samples_count": 5,
        }
        diff_regressed = compare_benchmarks(baseline, regressed_run)
        self.assertFalse(diff_regressed["improved"])
        self.assertTrue(diff_regressed["regressed"])
        self.assertLess(diff_regressed["delta_f1"], 0)

        # Case 3: Neutral
        diff_neutral = compare_benchmarks(baseline, baseline)
        self.assertTrue(diff_neutral["unchanged"])
        self.assertEqual(diff_neutral["delta_f1"], 0.0)


if __name__ == "__main__":
    unittest.main()
