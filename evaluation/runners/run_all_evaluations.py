
"""
run_all_evaluations.py

Main Orchestrator for the Complete LLMOps Evaluation Pipeline.

Execution order:
1. Component-Level Evaluation
2. Pipeline-Level Evaluation
3. Application-Level Evaluation

The orchestrator executes each evaluation sequentially,
tracks execution time and status, and generates a final summary.
"""

import subprocess
import sys
import time


# ---------------------------------------------------------
# Evaluation pipeline configuration
# ---------------------------------------------------------

EVALUATIONS = [
    {
        "name": "Component-Level Evaluation",
        "module": "evaluation.component.evals_component",
        "level": "Component",
    },
    {
        "name": "Pipeline-Level Evaluation",
        "module": "evaluation.pipeline.evaluate_rag_triad",
        "level": "Pipeline",
    },
    {
        "name": "Application-Level Evaluation",
        "module": "evaluation.application.evals_application",
        "level": "Application",
    },
]


# ---------------------------------------------------------
# Execute individual evaluation stage
# ---------------------------------------------------------

def run_evaluation(evaluation):
    """Execute one evaluation module and return its result."""

    name = evaluation["name"]
    module = evaluation["module"]

    print("\n" + "=" * 75)
    print(f"STARTING: {name}")
    print(f"MODULE  : {module}")
    print("=" * 75)

    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, "-m", module],
            check=False,
        )

        duration = time.time() - start_time

        status = (
            "PASSED"
            if result.returncode == 0
            else "FAILED"
        )

        return {
            "name": name,
            "level": evaluation["level"],
            "status": status,
            "duration": duration,
            "return_code": result.returncode,
        }

    except Exception as error:

        duration = time.time() - start_time

        print(f"\nExecution error: {error}")

        return {
            "name": name,
            "level": evaluation["level"],
            "status": "ERROR",
            "duration": duration,
            "return_code": -1,
        }


# ---------------------------------------------------------
# Main evaluation pipeline
# ---------------------------------------------------------

def main():

    print("\n" + "#" * 75)
    print("             COMPLETE LLMOPS EVALUATION PIPELINE")
    print("#" * 75)

    overall_start = time.time()
    results = []

    # Execute all evaluation stages sequentially.
    for evaluation in EVALUATIONS:

        result = run_evaluation(evaluation)
        results.append(result)

    total_duration = time.time() - overall_start

    # -----------------------------------------------------
    # Final consolidated evaluation summary
    # -----------------------------------------------------

    print("\n" + "#" * 75)
    print("                  FINAL EVALUATION SUMMARY")
    print("#" * 75)

    print(
        f"{'LEVEL':15} | "
        f"{'EVALUATION':35} | "
        f"{'STATUS':10} | "
        f"{'DURATION':12}"
    )

    print("-" * 75)

    for result in results:

        print(
            f"{result['level']:15} | "
            f"{result['name']:35} | "
            f"{result['status']:10} | "
            f"{result['duration']:.2f} sec"
        )

    # Calculate overall statistics.
    passed = sum(
        result["status"] == "PASSED"
        for result in results
    )

    failed = sum(
        result["status"] == "FAILED"
        for result in results
    )

    errors = sum(
        result["status"] == "ERROR"
        for result in results
    )

    # Determine overall pipeline status.
    overall_status = (
        "PASSED"
        if passed == len(results)
        else "FAILED"
    )

    print("\n" + "-" * 75)
    print(f"Total Evaluation Stages : {len(results)}")
    print(f"Passed                  : {passed}")
    print(f"Failed                  : {failed}")
    print(f"Execution Errors        : {errors}")
    print(f"Total Duration          : {total_duration:.2f} seconds")

    print("-" * 75)
    print(f"OVERALL PIPELINE STATUS: {overall_status}")
    print("#" * 75)

    # Return nonzero exit code if any stage fails.
    if overall_status == "FAILED":
        sys.exit(1)


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------

if __name__ == "__main__":
    main()
