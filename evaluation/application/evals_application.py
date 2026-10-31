
"""
Application-Level Evaluation Orchestrator

Purpose:
    Runs all application-level evaluations:
    1. Quality evaluation
    2. Safety evaluation
    3. Operations evaluation

The runner executes each evaluation module sequentially,
records its execution status and provides a final summary.
"""

import subprocess
import sys
import time
from dataclasses import dataclass


# ---------------------------------------------------------
# Evaluation configuration
# ---------------------------------------------------------

@dataclass
class EvaluationResult:
    """Stores the execution result of an evaluation module."""

    name: str
    module: str
    status: str
    duration: float
    return_code: int


# Application-level evaluation modules
APPLICATION_EVALUATIONS = [
    {
        "name": "Application Quality",
        "module": "evaluation.application.quality.evaluate_quality",
    },
    {
        "name": "Application Safety",
        "module": "evaluation.application.safety.evals_safety",
    },
    {
        "name": "Application Operations",
        "module": "evaluation.application.operations.evaluate_operations",
    },
]

# ---------------------------------------------------------
# Run individual evaluation module
# ---------------------------------------------------------

def run_evaluation(name: str, module: str) -> EvaluationResult:
    """
    Executes an evaluation module as a separate Python process.

    Returns:
        EvaluationResult containing execution status and duration.
    """

    print("\n" + "=" * 70)
    print(f"STARTING: {name}")
    print(f"MODULE:   {module}")
    print("=" * 70)

    start_time = time.perf_counter()

    try:
        # Execute the module using the current Python interpreter.
        process = subprocess.run(
            [sys.executable, "-m", module],
            check=False,
        )

        duration = time.perf_counter() - start_time

        # A zero exit code means the module completed successfully.
        status = "PASSED" if process.returncode == 0 else "FAILED"

        return EvaluationResult(
            name=name,
            module=module,
            status=status,
            duration=duration,
            return_code=process.returncode,
        )

    except Exception as exc:
        duration = time.perf_counter() - start_time

        print(f"\nExecution error: {exc}")

        return EvaluationResult(
            name=name,
            module=module,
            status="EXECUTION_ERROR",
            duration=duration,
            return_code=-1,
        )


# ---------------------------------------------------------
# Run all application-level evaluations
# ---------------------------------------------------------

def run_application_evaluations():
    """
    Runs quality, safety and operations evaluations sequentially.
    """

    print("\n" + "#" * 70)
    print("APPLICATION-LEVEL EVALUATION")
    print("#" * 70)

    results = []
    total_start_time = time.perf_counter()

    for evaluation in APPLICATION_EVALUATIONS:

        result = run_evaluation(
            name=evaluation["name"],
            module=evaluation["module"],
        )

        results.append(result)

    total_duration = time.perf_counter() - total_start_time

    # -----------------------------------------------------
    # Final evaluation summary
    # -----------------------------------------------------

    print("\n" + "=" * 70)
    print("APPLICATION EVALUATION SUMMARY")
    print("=" * 70)

    print(
        f"{'Evaluation':<28}"
        f"{'Status':<20}"
        f"{'Duration (sec)':>15}"
    )

    print("-" * 70)

    for result in results:
        print(
            f"{result.name:<28}"
            f"{result.status:<20}"
            f"{result.duration:>15.2f}"
        )

    passed = sum(r.status == "PASSED" for r in results)
    failed = sum(r.status == "FAILED" for r in results)
    errors = sum(r.status == "EXECUTION_ERROR" for r in results)

    print("-" * 70)
    print(f"Total evaluations : {len(results)}")
    print(f"Passed            : {passed}")
    print(f"Failed            : {failed}")
    print(f"Execution errors  : {errors}")
    print(f"Total duration    : {total_duration:.2f} seconds")

    # Overall status is successful only when every module passes.
    overall_pass = all(r.status == "PASSED" for r in results)

    print("\n" + "=" * 70)

    if overall_pass:
        print("APPLICATION EVALUATION: PASSED")
    else:
        print("APPLICATION EVALUATION: FAILED")

    print("=" * 70)

    return overall_pass


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------

if __name__ == "__main__":

    success = run_application_evaluations()

    # Return a non-zero exit code if any evaluation fails.
    sys.exit(0 if success else 1)
