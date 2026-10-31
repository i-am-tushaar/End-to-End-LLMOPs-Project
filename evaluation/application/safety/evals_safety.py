
"""
Safety Evaluation Runner
------------------------
Runs all application-level safety evaluations sequentially.

It checks:
1. Whether each evaluation module executes successfully.
2. Whether the generated JSON report exists.
3. Whether evaluation cases passed, failed, or encountered errors.

A module execution success does not automatically mean
that the evaluation itself passed.
"""

import json
import subprocess
import sys
import time

from pathlib import Path


# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Evaluation reports directory
REPORTS_DIR = PROJECT_ROOT / "evaluation" / "reports"


# Safety evaluation modules and their corresponding JSON reports
SAFETY_EVALUATIONS = [
    {
        "name": "Data Leakage Evaluation",
        "module": "evaluation.application.safety.evaluate_leakage",
        "report": "application_leakage_results.json",
    },
    {
        "name": "Toxicity Evaluation",
        "module": "evaluation.application.safety.evaluate_toxicity",
        "report": "application_toxicity_results.json",
    },
    {
        "name": "Scope Adherence Evaluation",
        "module": "evaluation.application.safety.evaluate_scope",
        "report": "application_scope_results.json",
    },
    {
        "name": "Application Safety Evaluation",
        "module": "evaluation.application.safety.evaluate_safety",
        "report": "application_safety_results.json",
    },
]


def find_summary(data):
    """
    Find the evaluation summary inside a JSON report.

    Supports reports where summary information is stored
    either at the root level or inside a nested dictionary.
    """

    if not isinstance(data, dict):
        return None

    summary_keys = {
        "passed_cases",
        "failed_cases",
        "error_cases",
        "overall_pass",
    }

    if len(summary_keys.intersection(data.keys())) >= 2:
        return data

    # Prefer an explicitly named summary dictionary.
    summary = data.get("summary")

    if isinstance(summary, dict):
        return summary

    # Search nested dictionaries.
    for value in data.values():
        if isinstance(value, dict):
            result = find_summary(value)

            if result is not None:
                return result

    return None


def read_evaluation_report(report_name):
    """Read and validate an evaluation JSON report."""

    report_path = REPORTS_DIR / report_name

    if not report_path.exists():
        return {
            "status": "ERROR",
            "message": f"Report not found: {report_path}",
        }

    try:
        with report_path.open("r", encoding="utf-8") as file:
            report_data = json.load(file)

    except (json.JSONDecodeError, OSError) as error:
        return {
            "status": "ERROR",
            "message": f"Unable to read report: {error}",
        }

    summary = find_summary(report_data)

    if summary is None:
        return {
            "status": "ERROR",
            "message": "Could not find evaluation summary in JSON report.",
        }

    passed = int(summary.get("passed_cases", 0) or 0)
    failed = int(summary.get("failed_cases", 0) or 0)
    errors = int(summary.get("error_cases", 0) or 0)

    partial_errors = int(
        summary.get("partial_error_cases", 0) or 0
    )

    metric_errors = int(
        summary.get("metric_errors", 0) or 0
    )

    overall_pass = summary.get("overall_pass")

    # Classify the actual evaluation outcome.
    has_errors = (
        errors > 0
        or partial_errors > 0
        or metric_errors > 0
    )

    has_failures = failed > 0 or overall_pass is False

    if has_failures and has_errors:
        status = "FAILED + ERROR"
    elif has_failures:
        status = "FAILED"
    elif has_errors:
        status = "ERROR"
    else:
        status = "PASSED"

    return {
        "status": status,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "partial_errors": partial_errors,
        "metric_errors": metric_errors,
    }


def run_evaluation(evaluation):
    """Execute one evaluation module and inspect its report."""

    name = evaluation["name"]
    module = evaluation["module"]
    report = evaluation["report"]

    print("\n" + "=" * 75)
    print(f"Running: {name}")
    print("=" * 75)

    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, "-m", module],
            cwd=PROJECT_ROOT,
            check=False,
        )

        duration = round(time.time() - start_time, 2)

        if result.returncode != 0:
            return {
                "name": name,
                "status": "EXECUTION_ERROR",
                "duration": duration,
                "details": f"Module exited with code {result.returncode}",
            }

        # Check the actual evaluation results.
        report_result = read_evaluation_report(report)

        return {
            "name": name,
            "status": report_result["status"],
            "duration": duration,
            "details": report_result,
        }

    except Exception as error:
        duration = round(time.time() - start_time, 2)

        return {
            "name": name,
            "status": "EXECUTION_ERROR",
            "duration": duration,
            "details": str(error),
        }


def display_summary(results, total_duration):
    """Display the final safety evaluation summary."""

    print("\n")
    print("=" * 75)
    print("SAFETY EVALUATION SUMMARY")
    print("=" * 75)

    print(
        f"{'Evaluation':<35}"
        f"{'Status':<20}"
        f"{'Duration (sec)':>15}"
    )

    print("-" * 75)

    for result in results:
        print(
            f"{result['name']:<35}"
            f"{result['status']:<20}"
            f"{result['duration']:>15.2f}"
        )

        details = result.get("details", {})

        if isinstance(details, dict) and "passed" in details:
            print(
                f"  Passed: {details['passed']} | "
                f"Failed: {details['failed']} | "
                f"Errors: {details['errors']} | "
                f"Partial errors: {details['partial_errors']} | "
                f"Metric errors: {details['metric_errors']}"
            )
        elif details:
            print(f"  Details: {details}")

    passed = sum(
        result["status"] == "PASSED"
        for result in results
    )

    failed = sum(
        result["status"] in {"FAILED", "FAILED + ERROR"}
        for result in results
    )

    errors = sum(
        result["status"] in {"ERROR", "EXECUTION_ERROR", "FAILED + ERROR"}
        for result in results
    )

    print("-" * 75)
    print(f"Total Evaluations : {len(results)}")
    print(f"Passed            : {passed}")
    print(f"Failed            : {failed}")
    print(f"Errors            : {errors}")
    print(f"Total Duration    : {total_duration:.2f} seconds")
    print("=" * 75)

    if passed == len(results):
        print("\n[SUCCESS] All safety evaluations passed.")
    else:
        print("\n[WARNING] Some safety evaluations did not pass.")
        print("Check the individual JSON reports for details.")


def main():
    """Run all safety evaluations sequentially."""

    print("\nStarting Application Safety Evaluation Suite")

    overall_start = time.time()
    results = []

    for evaluation in SAFETY_EVALUATIONS:
        result = run_evaluation(evaluation)
        results.append(result)

    total_duration = time.time() - overall_start

    display_summary(results, total_duration)

    # Return a non-zero exit code if any evaluation did not pass.
    if any(result["status"] != "PASSED" for result in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
