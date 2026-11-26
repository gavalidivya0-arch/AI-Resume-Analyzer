"""Executable CLI script to run automated accuracy benchmarks (Issue #38).

Usage:
    python -m benchmarks.run_benchmark [options]
    python benchmarks/run_benchmark.py [options]

Options:
    -o, --output <path>    Save evaluation results as JSON for cross-commit comparison.
    -c, --compare <path>   Compare current results against a baseline benchmark JSON file.
    -v, --verbose          Display per-sample breakdown and skill mismatches.
    -q, --quiet            Only display the summary metrics table.
"""

import argparse
import json
import os
import sys

from benchmarks.evaluator import (
    compare_benchmarks,
    evaluate_benchmark,
    format_benchmark_summary,
)


def main():
    parser = argparse.ArgumentParser(
        description="Run automated resume analysis accuracy benchmark against synthetic test data."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Path to save evaluation summary as JSON.",
    )
    parser.add_argument(
        "-c",
        "--compare",
        type=str,
        default=None,
        help="Path to previous benchmark JSON result to compare against.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed per-sample accuracy breakdowns.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress sample-level output.",
    )

    args = parser.parse_args()

    results = evaluate_benchmark()

    # Print human-readable summary
    summary_text = format_benchmark_summary(results, verbose=args.verbose and not args.quiet)
    print(summary_text)

    # Compare against baseline if specified
    if args.compare:
        if os.path.exists(args.compare):
            try:
                with open(args.compare, "r", encoding="utf-8") as f:
                    baseline_data = json.load(f)
                diff = compare_benchmarks(baseline_data, results)
                print("\n" + "=" * 68)
                print("           ACCURACY DELTA VS BASELINE BENCHMARK           ")
                print("=" * 68)
                status = "IMPROVED" if diff["improved"] else ("REGRESSED" if diff["regressed"] else "NEUTRAL")
                print(f"Overall Status   : {status}")
                print(f"Baseline F1      : {diff['baseline_f1']*100:.1f}%")
                print(f"Current F1       : {diff['current_f1']*100:.1f}%")
                print(f"Delta F1-Score   : {diff['delta_f1']*100:+.2f}%")
                print(f"Delta Precision  : {diff['delta_precision']*100:+.2f}%")
                print(f"Delta Recall     : {diff['delta_recall']*100:+.2f}%")
                print("=" * 68)
            except Exception as exc:
                print(f"Warning: Failed to load comparison file '{args.compare}': {exc}", file=sys.stderr)
        else:
            print(f"Warning: Comparison file '{args.compare}' does not exist.", file=sys.stderr)

    # Save output to JSON file if requested
    if args.output:
        out_dir = os.path.dirname(args.output)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\n[+] Benchmark results saved to: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
