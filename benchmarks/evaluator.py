"""Evaluation engine for calculating precision, recall, and benchmark summaries (Issue #38).

Provides:
- Exact evaluation of True Positives, False Positives, False Negatives.
- Precision, Recall, and F1-score computation.
- Macro and micro average aggregation across resumes.
- Formatted summary generation and cross-run comparison tools.
"""

import time
from typing import Any, Callable, Dict, List, Optional, Set

from analyzer.skills_extractor import extract_skills
from benchmarks.dataset import SYNTHETIC_RESUMES, BenchmarkSample


def calculate_metrics(extracted: Set[str], expected: Set[str]) -> Dict[str, Any]:
    """Calculate extraction evaluation metrics for a single sample.

    Args:
        extracted: Set of skill names detected by the analyzer.
        expected: Set of ground-truth skill names expected.

    Returns:
        Dictionary containing counts, sets, precision, recall, and f1_score.
    """
    tp_set = extracted & expected
    fp_set = extracted - expected
    fn_set = expected - extracted

    tp = len(tp_set)
    fp = len(fp_set)
    fn = len(fn_set)

    # Precision: proportion of extracted skills that are correct
    if tp + fp == 0:
        # If nothing was extracted and nothing was expected, precision is 1.0; else 0.0
        precision = 1.0 if fn == 0 else 0.0
    else:
        precision = tp / (tp + fp)

    # Recall: proportion of expected skills that were successfully extracted
    if tp + fn == 0:
        recall = 1.0
    else:
        recall = tp / (tp + fn)

    # F1 Score: harmonic mean of precision and recall
    if precision + recall == 0.0:
        f1_score = 0.0
    else:
        f1_score = 2.0 * (precision * recall) / (precision + recall)

    return {
        "true_positives": sorted(list(tp_set)),
        "false_positives": sorted(list(fp_set)),
        "false_negatives": sorted(list(fn_set)),
        "tp_count": tp,
        "fp_count": fp,
        "fn_count": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1_score, 4),
    }


def evaluate_benchmark(
    dataset: Optional[List[BenchmarkSample]] = None,
    extractor_fn: Optional[Callable[[str], List[str]]] = None,
) -> Dict[str, Any]:
    """Evaluate extraction accuracy against the synthetic benchmark dataset.

    Args:
        dataset: List of BenchmarkSample items (defaults to SYNTHETIC_RESUMES).
        extractor_fn: Skill extraction function (defaults to extract_skills).

    Returns:
        Complete benchmark evaluation results including per-sample and aggregate metrics.
    """
    samples = dataset if dataset is not None else SYNTHETIC_RESUMES
    extractor = extractor_fn if extractor_fn is not None else extract_skills

    start_time = time.time()
    per_sample_results: List[Dict[str, Any]] = []

    global_tp = 0
    global_fp = 0
    global_fn = 0

    precision_sum = 0.0
    recall_sum = 0.0
    f1_sum = 0.0

    for sample in samples:
        extracted_list = extractor(sample.text)
        extracted_set = set(extracted_list)
        metrics = calculate_metrics(extracted_set, sample.expected_skills)

        sample_result = {
            "sample_id": sample.sample_id,
            "role": sample.role,
            "expected_skills": sorted(list(sample.expected_skills)),
            "extracted_skills": sorted(list(extracted_set)),
            **metrics,
        }
        per_sample_results.append(sample_result)

        global_tp += metrics["tp_count"]
        global_fp += metrics["fp_count"]
        global_fn += metrics["fn_count"]

        precision_sum += metrics["precision"]
        recall_sum += metrics["recall"]
        f1_sum += metrics["f1_score"]

    elapsed_time = round(time.time() - start_time, 4)
    num_samples = len(samples)

    if num_samples > 0:
        macro_precision = round(precision_sum / num_samples, 4)
        macro_recall = round(recall_sum / num_samples, 4)
        macro_f1 = round(f1_sum / num_samples, 4)
    else:
        macro_precision = 0.0
        macro_recall = 0.0
        macro_f1 = 0.0

    # Micro averages (pooled counts)
    if global_tp + global_fp == 0:
        micro_precision = 1.0 if global_fn == 0 else 0.0
    else:
        micro_precision = round(global_tp / (global_tp + global_fp), 4)

    if global_tp + global_fn == 0:
        micro_recall = 1.0
    else:
        micro_recall = round(global_tp / (global_tp + global_fn), 4)

    if micro_precision + micro_recall == 0.0:
        micro_f1 = 0.0
    else:
        micro_f1 = round(
            2.0 * (micro_precision * micro_recall) / (micro_precision + micro_recall),
            4,
        )

    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "samples_count": num_samples,
        "elapsed_seconds": elapsed_time,
        "macro_metrics": {
            "precision": macro_precision,
            "recall": macro_recall,
            "f1_score": macro_f1,
        },
        "micro_metrics": {
            "precision": micro_precision,
            "recall": micro_recall,
            "f1_score": micro_f1,
            "total_tp": global_tp,
            "total_fp": global_fp,
            "total_fn": global_fn,
        },
        "samples": per_sample_results,
    }


def format_benchmark_summary(result: Dict[str, Any], verbose: bool = False) -> str:
    """Format benchmark evaluation results into a human-readable table."""
    macro = result["macro_metrics"]
    micro = result["micro_metrics"]

    lines = [
        "=" * 68,
        "          RESUME ANALYSIS ACCURACY BENCHMARK SUMMARY          ",
        "=" * 68,
        f"Evaluated Samples : {result['samples_count']}",
        f"Evaluation Time   : {result['elapsed_seconds']}s",
        f"Timestamp         : {result.get('timestamp', 'N/A')}",
        "-" * 68,
        "OVERALL ACCURACY METRICS:",
        f"  Macro Precision : {macro['precision'] * 100:.1f}%",
        f"  Macro Recall    : {macro['recall'] * 100:.1f}%",
        f"  Macro F1-Score  : {macro['f1_score'] * 100:.1f}%",
        "",
        f"  Micro Precision : {micro['precision'] * 100:.1f}% (TP={micro['total_tp']}, FP={micro['total_fp']})",
        f"  Micro Recall    : {micro['recall'] * 100:.1f}% (FN={micro['total_fn']})",
        f"  Micro F1-Score  : {micro['f1_score'] * 100:.1f}%",
        "=" * 68,
    ]

    if verbose and "samples" in result:
        lines.append("PER-SAMPLE BREAKDOWN:")
        lines.append(f"{'Sample ID':<26} {'Role':<24} {'P':<6} {'R':<6} {'F1':<6}")
        lines.append("-" * 68)
        for s in result["samples"]:
            lines.append(
                f"{s['sample_id'][:25]:<26} {s['role'][:23]:<24} "
                f"{s['precision']*100:>5.1f}% {s['recall']*100:>5.1f}% {s['f1_score']*100:>5.1f}%"
            )
            if s["false_positives"]:
                lines.append(f"   [+] False Positives: {', '.join(s['false_positives'])}")
            if s["false_negatives"]:
                lines.append(f"   [-] False Negatives: {', '.join(s['false_negatives'])}")
        lines.append("=" * 68)

    return "\n".join(lines)


def compare_benchmarks(baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two benchmark runs to track accuracy improvements or regressions across code changes.

    Args:
        baseline: Benchmark results dict from baseline run.
        current: Benchmark results dict from current run.

    Returns:
        Dictionary detailing delta changes for precision, recall, and F1.
    """
    base_macro = baseline.get("macro_metrics", {})
    curr_macro = current.get("macro_metrics", {})

    delta_precision = round(curr_macro.get("precision", 0.0) - base_macro.get("precision", 0.0), 4)
    delta_recall = round(curr_macro.get("recall", 0.0) - base_macro.get("recall", 0.0), 4)
    delta_f1 = round(curr_macro.get("f1_score", 0.0) - base_macro.get("f1_score", 0.0), 4)

    return {
        "baseline_f1": base_macro.get("f1_score", 0.0),
        "current_f1": curr_macro.get("f1_score", 0.0),
        "delta_f1": delta_f1,
        "delta_precision": delta_precision,
        "delta_recall": delta_recall,
        "improved": delta_f1 > 0,
        "regressed": delta_f1 < 0,
        "unchanged": delta_f1 == 0,
    }
