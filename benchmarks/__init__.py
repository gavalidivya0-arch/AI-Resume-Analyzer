"""Automated Resume Analysis Benchmarking (Issue #38).

Provides:
- Synthetic test resumes with ground truth annotations.
- Precision, recall, and F1-score evaluation metrics.
- Benchmark summary generation and export.
- Comparison utilities across code changes.
"""

from benchmarks.dataset import SYNTHETIC_RESUMES, BenchmarkSample
from benchmarks.evaluator import (
    calculate_metrics,
    compare_benchmarks,
    evaluate_benchmark,
    format_benchmark_summary,
)

__all__ = [
    "SYNTHETIC_RESUMES",
    "BenchmarkSample",
    "calculate_metrics",
    "evaluate_benchmark",
    "compare_benchmarks",
    "format_benchmark_summary",
]
