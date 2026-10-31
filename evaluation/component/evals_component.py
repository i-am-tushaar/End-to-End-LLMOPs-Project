
"""
evals_component.py

Component-Level Evaluation Runner.

Purpose:
    Execute both component-level evaluations:
    1. Retriever Evaluation
    2. Generator Evaluation

The runner executes both modules sequentially,
tracks execution time, and generates a final summary.
"""

import subprocess
import sys
import time


# ---------------------------------------------------------
# Component evaluation configuration
# ---------------------------------------------------------

COMPONENT_EVALUATIONS = [
    {
        "name": "Retriever Evaluation",
        "module": "evaluation.component.evaluate_retriever",
    },
    {
        "name": "Generator Evaluation",
        "module": "evaluation.component.evaluate_generator",
    },
]


# ---------------------------------------------------------
# Run individual component evaluation
# ---------------------------------------------------------

def run_evaluation(evaluation):

    name = evaluation["name"]
    module = evaluation["module"]

    print("\n" + "=" * 70)
    print(f"STARTING: {name}")
    print("=" * 70)

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
            "status": status,
            "duration": duration,
            "return_code": result.returncode,
        }

    except Exception as error:

        duration = time.time() - start_time

        print(f"Execution error: {error}")

        return {
            "name": name,
            "status": "ERROR",
            "duration": duration,
            "return_code": -1,
        }


# ---------------------------------------------------------
# Main component evaluation pipeline
# ---------------------------------------------------------

def main():

    print("\n" + "#" * 70)
    print("       COMPONENT-LEVEL EVALUATION PIPELINE")
    print("#" * 70)

    overall_start = time.time()
    results = []

    # Execute retriever and generator evaluations.
    for evaluation in COMPONENT_EVALUATIONS:

        result = run_evaluation(evaluation)
        results.append(result)

    total_duration = time.time() - overall_start

    # -----------------------------------------------------
    # Final evaluation summary
    # -----------------------------------------------------

    print("\n" + "#" * 70)
    print("          COMPONENT EVALUATION SUMMARY")
    print("#" * 70)

    for result in results:

        print(
            f"{result['name']:30} | "
            f"{result['status']:8} | "
            f"{result['duration']:.2f} sec"
        )

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

    print("\n" + "-" * 70)
    print(f"Total Evaluations : {len(results)}")
    print(f"Passed            : {passed}")
    print(f"Failed            : {failed}")
    print(f"Errors            : {errors}")
    print(f"Total Duration    : {total_duration:.2f} seconds")

    overall_status = (
        "PASSED"
        if passed == len(results)
        else "FAILED"
    )

    print("-" * 70)
    print(f"OVERALL STATUS: {overall_status}")
    print("#" * 70)

    # Return failure if any component evaluation fails.
    if overall_status == "FAILED":
        sys.exit(1)


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------

if __name__ == "__main__":
    main()
