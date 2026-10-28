"""
Application Operations Evaluation
=================================

Purpose:
    Evaluate the operational performance of the End-to-End LLMOps RAG
    application by executing every dataset question multiple times.

Metrics:
    - Total requests
    - Successful and failed requests
    - Success rate and error rate
    - Average latency
    - P50, P95, and P99 latency
    - Total evaluation duration
    - Throughput (requests per second)
    - Per-request latency and error details

Execution:
    uv run python -m evaluation.application.operations.evaluate_operations

Output:
    evaluation/reports/application_operations_results.json
"""

import json
import logging
import os
import statistics
import time

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from multi_doc_chat.src.document_chat.retrieval import ConversationalRAG


# ============================================================
# 1. PATHS AND CONFIGURATION
# ============================================================

# Project root:
# End-to-End-LLMOPs-Project/
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Dataset containing the application operations test questions.
DATASET_PATH = (
    PROJECT_ROOT
    / "evaluation"
    / "datasets"
    / "application_operations_eval.json"
)

# JSON file where evaluation results will be saved.
REPORT_PATH = (
    PROJECT_ROOT
    / "evaluation"
    / "reports"
    / "application_operations_results.json"
)

# Existing FAISS index used by the RAG application.
# You can override this path using EVALUATION_FAISS_INDEX.
DEFAULT_FAISS_INDEX = (
    PROJECT_ROOT
    / "faiss_index"
    / "session_20261026_215230_88296173"
)

# Execute every question this many times.
REPEATS_PER_QUESTION = 3

# Existing retriever configuration.
RETRIEVER_K = 3
SEARCH_TYPE = "mmr"
FETCH_K = 10
LAMBDA_MULT = 0.5


# ============================================================
# 2. LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# 3. LOAD AND VALIDATE THE EVALUATION DATASET
# ============================================================

def load_dataset(dataset_path: Path) -> list[dict[str, Any]]:
    """
    Load and validate the JSON evaluation dataset.

    Supported formats:
        A list of test cases, or a dictionary containing a
        'cases' or 'test_cases' list.

    Each test case must contain a question, input, or query field.
    """

    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Evaluation dataset not found: {dataset_path}"
        )

    with dataset_path.open("r", encoding="utf-8") as file:
        dataset = json.load(file)

    if isinstance(dataset, dict):
        dataset = dataset.get(
            "cases",
            dataset.get("test_cases"),
        )

    if not isinstance(dataset, list) or not dataset:
        raise ValueError(
            "The evaluation dataset must contain a non-empty list "
            "of test cases."
        )

    validated_cases = []
    seen_ids = set()

    for index, case in enumerate(dataset, start=1):
        if not isinstance(case, dict):
            raise ValueError(
                f"Test case {index} must be a JSON object."
            )

        question = (
            case.get("question")
            or case.get("input")
            or case.get("query")
        )

        if not isinstance(question, str) or not question.strip():
            raise ValueError(
                f"Test case {index} has no valid question/input/query."
            )

        case_id = str(case.get("id", f"ops_{index:03d}"))

        if case_id in seen_ids:
            raise ValueError(
                f"Duplicate test case ID found: {case_id}"
            )

        seen_ids.add(case_id)

        validated_cases.append(
            {
                "id": case_id,
                "question": question.strip(),
            }
        )

    return validated_cases


# ============================================================
# 4. INITIALIZE THE RAG APPLICATION
# ============================================================

def initialize_rag() -> ConversationalRAG:
    """
    Initialize the existing ConversationalRAG application and
    load the configured FAISS retriever.
    """

    configured_index = os.getenv("EVALUATION_FAISS_INDEX")

    index_path = (
        Path(configured_index)
        if configured_index
        else DEFAULT_FAISS_INDEX
    )

    # Resolve relative paths from the project root.
    if not index_path.is_absolute():
        index_path = PROJECT_ROOT / index_path

    if not index_path.exists():
        raise FileNotFoundError(
            f"FAISS index directory not found: {index_path}\n"
            "Set EVALUATION_FAISS_INDEX to the correct FAISS "
            "session directory."
        )

    logger.info("Initializing ConversationalRAG...")
    logger.info("FAISS index: %s", index_path)

    import uuid

    session_id = f"operations_eval_{uuid.uuid4().hex[:8]}"
    rag = ConversationalRAG(session_id=session_id)

    # Use the retriever configuration already established in
    # the project.
    rag.load_retriever_from_faiss(
        index_path=str(index_path),
        k=RETRIEVER_K,
        search_type=SEARCH_TYPE,
        fetch_k=FETCH_K,
        lambda_mult=LAMBDA_MULT,
    )

    logger.info("RAG application initialized successfully.")

    return rag


# ============================================================
# 5. EXTRACT THE ANSWER FROM THE RAG RESPONSE
# ============================================================

def extract_answer(response: Any) -> str:
    """
    Normalize common RAG response formats into a string.

    Supports direct strings and dictionaries containing common
    answer keys. If your application uses another response schema,
    add its key here.
    """

    if isinstance(response, str):
        return response

    if isinstance(response, dict):
        for key in ("answer", "response", "output", "result"):
            value = response.get(key)

            if isinstance(value, str):
                return value

        return json.dumps(response, ensure_ascii=False, default=str)

    # Handles response objects with a content attribute.
    content = getattr(response, "content", None)

    if isinstance(content, str):
        return content

    return str(response)


# ============================================================
# 6. CALCULATE PERCENTILES
# ============================================================

def calculate_percentile(
    values: list[float],
    percentile: float,
) -> float | None:
    """
    Calculate a percentile using linear interpolation.

    This avoids requiring NumPy solely for percentile calculations.
    Percentiles are descriptive estimates, especially with small
    evaluation datasets.
    """

    if not values:
        return None

    sorted_values = sorted(values)

    if len(sorted_values) == 1:
        return round(sorted_values[0], 2)

    position = (len(sorted_values) - 1) * percentile / 100

    lower_index = int(position)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)

    fraction = position - lower_index

    result = (
        sorted_values[lower_index] * (1 - fraction)
        + sorted_values[upper_index] * fraction
    )

    return round(result, 2)


# ============================================================
# 7. CALCULATE OPERATIONAL METRICS
# ============================================================

def calculate_metrics(
    attempts: list[dict[str, Any]],
    total_duration_seconds: float,
) -> dict[str, Any]:
    """
    Calculate aggregate operational metrics across all attempts.

    A request is technically successful if the RAG invocation
    completes without raising an exception.

    A response such as "I don't know." is still a technically
    successful invocation; answer quality is evaluated separately.
    """

    total_requests = len(attempts)

    successful_attempts = [
        attempt
        for attempt in attempts
        if attempt["success"]
    ]

    failed_attempts = [
        attempt
        for attempt in attempts
        if not attempt["success"]
    ]

    successful_latencies = [
        attempt["latency_ms"]
        for attempt in successful_attempts
    ]

    successful_count = len(successful_attempts)
    failed_count = len(failed_attempts)

    success_rate = (
        successful_count / total_requests * 100
        if total_requests
        else 0.0
    )

    error_rate = (
        failed_count / total_requests * 100
        if total_requests
        else 0.0
    )

    average_latency = (
        statistics.mean(successful_latencies)
        if successful_latencies
        else None
    )

    # Throughput is based on completed requests divided by the
    # total wall-clock duration of the request execution loop.
    throughput = (
        successful_count / total_duration_seconds
        if total_duration_seconds > 0
        else 0.0
    )

    return {
        "total_requests": total_requests,
        "successful_requests": successful_count,
        "failed_requests": failed_count,
        "success_rate_percent": round(success_rate, 2),
        "error_rate_percent": round(error_rate, 2),
        "average_latency_ms": (
            round(average_latency, 2)
            if average_latency is not None
            else None
        ),
        "p50_latency_ms": calculate_percentile(
            successful_latencies, 50
        ),
        "p95_latency_ms": calculate_percentile(
            successful_latencies, 95
        ),
        "p99_latency_ms": calculate_percentile(
            successful_latencies, 99
        ),
        "total_duration_seconds": round(
            total_duration_seconds, 2
        ),
        "throughput_requests_per_second": round(
            throughput, 3
        ),
        "api_cost": {
            "status": "not_measured",
            "reason": (
                "Actual token usage or provider billing data "
                "has not been captured by this evaluator."
            ),
        },
    }


# ============================================================
# 8. RUN REPEATED OPERATIONS EVALUATION
# ============================================================

def evaluate_operations() -> dict[str, Any]:
    """
    Execute every test question three times.

    Each attempt records its own latency, response, status,
    and error details when applicable.
    """

    logger.info("=" * 65)
    logger.info("STARTING APPLICATION OPERATIONS EVALUATION")
    logger.info("=" * 65)

    # Load test questions.
    test_cases = load_dataset(DATASET_PATH)

    logger.info("Dataset: %s", DATASET_PATH)
    logger.info("Test cases: %d", len(test_cases))
    logger.info("Repeats per question: %d", REPEATS_PER_QUESTION)
    logger.info(
        "Expected total requests: %d",
        len(test_cases) * REPEATS_PER_QUESTION,
    )

    # Initialize the application before measuring request latency.
    # Initialization time is not included in per-request latency.
    rag = initialize_rag()

    attempts: list[dict[str, Any]] = []
    case_results: list[dict[str, Any]] = []

    # Measure the wall-clock duration of the request execution loop.
    evaluation_start = time.perf_counter()

    for case in test_cases:
        case_id = case["id"]
        question = case["question"]

        logger.info("-" * 65)
        logger.info("Test case: %s", case_id)
        logger.info("Question: %s", question)

        individual_attempts = []

        # Run each question multiple times.
        for repeat_number in range(1, REPEATS_PER_QUESTION + 1):
            logger.info(
                "Attempt %d/%d for %s",
                repeat_number,
                REPEATS_PER_QUESTION,
                case_id,
            )

            attempt_start = time.perf_counter()

            answer = None
            error_message = None
            success = False

            try:
                # Use the same RAG invocation interface as the
                # existing application operations evaluator.
                response = rag.invoke(
                    question,
                    chat_history=[],
                )

                answer = extract_answer(response)

                # Technical success means invoke() returned without
                # raising an exception, even if the answer is
                # "I don't know." or an empty string.
                success = True

            except Exception as exc:
                error_message = (
                    f"{type(exc).__name__}: {str(exc)}"
                )

                logger.exception(
                    "Request failed for %s, attempt %d",
                    case_id,
                    repeat_number,
                )

            attempt_end = time.perf_counter()

            latency_ms = round(
                (attempt_end - attempt_start) * 1000,
                2,
            )

            attempt_result = {
                "case_id": case_id,
                "repeat_number": repeat_number,
                "question": question,
                "success": success,
                "latency_ms": latency_ms,
                "answer": answer,
                "answer_is_empty": (
                    success and not (answer or "").strip()
                ),
                "error": error_message,
            }

            attempts.append(attempt_result)
            individual_attempts.append(attempt_result)

            logger.info(
                "Status: %s | Latency: %.2f ms",
                "SUCCESS" if success else "FAILED",
                latency_ms,
            )

        # Summarize the repeated attempts for this question.
        successful_case_attempts = [
            item
            for item in individual_attempts
            if item["success"]
        ]

        case_latencies = [
            item["latency_ms"]
            for item in successful_case_attempts
        ]

        case_results.append(
            {
                "case_id": case_id,
                "question": question,
                "attempts_requested": REPEATS_PER_QUESTION,
                "attempts_completed": len(individual_attempts),
                "successful_attempts": len(
                    successful_case_attempts
                ),
                "failed_attempts": (
                    len(individual_attempts)
                    - len(successful_case_attempts)
                ),
                "success_rate_percent": round(
                    len(successful_case_attempts)
                    / len(individual_attempts)
                    * 100,
                    2,
                ),
                "average_latency_ms": (
                    round(statistics.mean(case_latencies), 2)
                    if case_latencies
                    else None
                ),
                "p50_latency_ms": calculate_percentile(
                    case_latencies, 50
                ),
                "p95_latency_ms": calculate_percentile(
                    case_latencies, 95
                ),
                "p99_latency_ms": calculate_percentile(
                    case_latencies, 99
                ),
                "attempt_results": individual_attempts,
            }
        )

    evaluation_end = time.perf_counter()

    total_duration_seconds = (
        evaluation_end - evaluation_start
    )

    # Calculate metrics using all individual requests.
    metrics = calculate_metrics(
        attempts=attempts,
        total_duration_seconds=total_duration_seconds,
    )

    # Build the complete JSON report.
    report = {
        "evaluation_name": "Application Operations Evaluation",
        "evaluation_timestamp_utc": (
            datetime.now(timezone.utc).isoformat()
        ),
        "dataset_path": str(DATASET_PATH),
        "repeats_per_question": REPEATS_PER_QUESTION,
        "test_cases_count": len(test_cases),
        "expected_requests": (
            len(test_cases) * REPEATS_PER_QUESTION
        ),
        "retriever_configuration": {
            "k": RETRIEVER_K,
            "search_type": SEARCH_TYPE,
            "fetch_k": FETCH_K,
            "lambda_mult": LAMBDA_MULT,
        },
        "latency_methodology": {
            "unit": "milliseconds",
            "measured_operation": (
                "RAG invoke call, including retrieval and generation"
            ),
            "application_initialization_included": False,
            "percentiles_calculated_from": (
                "Successful request latencies across all attempts"
            ),
            "execution_mode": "sequential",
        },
        "metrics": metrics,
        "case_results": case_results,
        "all_attempts": attempts,
        "limitations": [
            (
                "Only the configured number of test cases and "
                "repetitions were evaluated."
            ),
            (
                "P95 and P99 estimates from a small sample are "
                "not reliable production-scale latency guarantees."
            ),
            (
                "Sequential testing does not measure concurrent "
                "load or maximum system capacity."
            ),
            (
                "Technical success does not establish answer "
                "correctness, completeness, or safety."
            ),
            (
                "API cost is not measured because actual token usage "
                "or provider billing data is not captured."
            ),
        ],
    }

    # Create the report directory if it does not exist.
    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Save the evaluation report.
    with REPORT_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            indent=4,
            ensure_ascii=False,
        )

    # Print the final summary.
    logger.info("=" * 65)
    logger.info("APPLICATION OPERATIONS EVALUATION COMPLETED")
    logger.info("=" * 65)
    logger.info("Total requests: %d", metrics["total_requests"])
    logger.info(
        "Successful requests: %d",
        metrics["successful_requests"],
    )
    logger.info(
        "Failed requests: %d",
        metrics["failed_requests"],
    )
    logger.info(
        "Success rate: %.2f%%",
        metrics["success_rate_percent"],
    )
    logger.info(
        "Error rate: %.2f%%",
        metrics["error_rate_percent"],
    )
    logger.info(
        "Average latency: %s ms",
        metrics["average_latency_ms"],
    )
    logger.info(
        "P50 latency: %s ms",
        metrics["p50_latency_ms"],
    )
    logger.info(
        "P95 latency: %s ms",
        metrics["p95_latency_ms"],
    )
    logger.info(
        "P99 latency: %s ms",
        metrics["p99_latency_ms"],
    )
    logger.info(
        "Throughput: %.3f requests/second",
        metrics["throughput_requests_per_second"],
    )
    logger.info("Report saved to: %s", REPORT_PATH)

    return report


# ============================================================
# 9. ENTRY POINT
# ============================================================

if __name__ == "__main__":
    evaluate_operations()