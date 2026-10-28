"""
Application Quality Evaluation
==============================

Evaluates the end-to-end RAG application using:
1. Correctness
2. Completeness
3. Style
4. Answer Relevancy
5. Faithfulness
6. Grounding / hallucination risk

Run from the project root:
    uv run python -m evaluation.application.quality.evaluate_quality
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams

from evaluation.judges.deepeval_groq_model import DeepEvalGroqModel
from multi_doc_chat.logger.custom_logger import GLOBAL_LOGGER as logger
from multi_doc_chat.src.document_chat.retrieval import ConversationalRAG


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATASET_PATH = (
    PROJECT_ROOT
    / "evaluation"
    / "datasets"
    / "application_quality_eval.json"
)

REPORT_PATH = (
    PROJECT_ROOT
    / "evaluation"
    / "reports"
    / "application_quality_results.json"
)

FAISS_INDEX_PATH = (
    PROJECT_ROOT
    / "faiss_index"
    / "session_20261026_215230_88296173"
)

JUDGE_MODEL_NAME = "openai/gpt-oss-20b"
METRIC_THRESHOLD = 0.70

RETRIEVER_K = 3
RETRIEVER_FETCH_K = 10
RETRIEVER_LAMBDA_MULT = 0.5


# ============================================================
# METRIC INITIALIZATION
# ============================================================

def initialize_metrics() -> dict[str, Any]:
    """Initialize the six application quality metrics using the Groq judge."""

    judge = DeepEvalGroqModel(model_name=JUDGE_MODEL_NAME)

    metrics: dict[str, Any] = {
        "correctness": GEval(
            name="Correctness",
            criteria=(
                "Evaluate the factual correctness of the actual answer against "
                "the expected answer. Penalize incorrect, contradictory, or "
                "factually inaccurate claims. Accept equivalent wording and "
                "correct paraphrasing."
            ),
            evaluation_steps=[
                "Understand the question and expected answer.",
                "Compare the actual answer with the expected answer.",
                "Identify factual errors and contradictions.",
                "Accept semantically equivalent explanations.",
                "Assign a score from 0 to 10, where 10 means fully correct "
                "and 0 means completely incorrect.",
            ],
            evaluation_params=[
                SingleTurnParams.INPUT,
                SingleTurnParams.ACTUAL_OUTPUT,
                SingleTurnParams.EXPECTED_OUTPUT,
            ],
            threshold=METRIC_THRESHOLD,
            model=judge,
            async_mode=False,
        ),
        "completeness": GEval(
            name="Completeness",
            criteria=(
                "Evaluate whether the actual answer covers the essential "
                "information required to answer the question. Compare it "
                "with the expected answer. Penalize missing important "
                "concepts, explanations, or details. Do not reward "
                "unnecessary verbosity."
            ),
            evaluation_steps=[
                "Identify the essential information required by the question.",
                "Review the expected answer to identify key concepts.",
                "Compare the actual answer with those key concepts.",
                "Identify important omissions or incomplete explanations.",
                "Do not penalize concise answers that cover the key points.",
                "Assign a score from 0 to 10, where 10 means all essential "
                "information is covered and 0 means essential information "
                "is almost entirely missing.",
            ],
            evaluation_params=[
                SingleTurnParams.INPUT,
                SingleTurnParams.ACTUAL_OUTPUT,
                SingleTurnParams.EXPECTED_OUTPUT,
            ],
            threshold=METRIC_THRESHOLD,
            model=judge,
            async_mode=False,
        ),
        "style": GEval(
            name="Style",
            criteria=(
                "Evaluate the clarity, readability, organization, professional "
                "tone, grammar, and appropriate conciseness of the actual "
                "answer. Do not judge factual correctness or completeness in "
                "this metric. Do not penalize a correct answer merely because "
                "it is short."
            ),
            evaluation_steps=[
                "Assess whether the answer is clear and easy to understand.",
                "Assess grammar and readability.",
                "Assess logical organization and flow.",
                "Assess professional and appropriate language.",
                "Assess whether the answer is appropriately concise.",
                "Assign a score from 0 to 10, where 10 means excellent clarity "
                "and readability and 0 means extremely poor writing.",
            ],
            evaluation_params=[
                SingleTurnParams.INPUT,
                SingleTurnParams.ACTUAL_OUTPUT,
            ],
            threshold=METRIC_THRESHOLD,
            model=judge,
            async_mode=False,
        ),
        "answer_relevancy": AnswerRelevancyMetric(
            threshold=METRIC_THRESHOLD,
            model=judge,
            include_reason=True,
            async_mode=False,
        ),
        "faithfulness": FaithfulnessMetric(
            threshold=METRIC_THRESHOLD,
            model=judge,
            include_reason=True,
            async_mode=False,
        ),
        # This is a positive-oriented grounding score: a higher score means
        # the answer is better supported by the retrieved context. The key
        # remains "hallucination" to preserve compatibility with existing
        # report consumers. Interpret it as grounding, not as risk severity.
        "hallucination": GEval(
            name="Groundedness",
            criteria=(
                "Evaluate whether the actual answer contains factual claims "
                "that are unsupported by or contradict the retrieved context. "
                "Give a high score when the answer is grounded in the context "
                "and a low score when it contains fabricated or contradicted "
                "claims. Correct paraphrasing and reasonable summaries of "
                "the context must not be considered hallucinations."
            ),
            evaluation_steps=[
                "Identify the factual claims in the actual answer.",
                "Compare each claim with the retrieved context.",
                "Identify claims that contradict the retrieved context.",
                "Identify specific claims that are not supported by the context.",
                "Distinguish unsupported claims from correct paraphrasing.",
                "Assign a score from 0 to 10, where 10 means all factual claims "
                "are supported by the retrieved context and 0 means the answer "
                "is substantially unsupported or contradicted.",
            ],
            evaluation_params=[
                SingleTurnParams.INPUT,
                SingleTurnParams.ACTUAL_OUTPUT,
                SingleTurnParams.RETRIEVAL_CONTEXT,
            ],
            threshold=METRIC_THRESHOLD,
            model=judge,
            async_mode=False,
        ),
    }

    logger.info(
        "application_quality_metrics_initialized",
        metric_count=len(metrics),
        metrics=list(metrics.keys()),
        threshold=METRIC_THRESHOLD,
    )
    return metrics


# ============================================================
# DATASET
# ============================================================

def load_dataset() -> list[dict[str, Any]]:
    """Load and validate application quality evaluation cases from JSON."""

    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Evaluation dataset not found: {DATASET_PATH}")

    with DATASET_PATH.open("r", encoding="utf-8") as file:
        dataset = json.load(file)

    if not isinstance(dataset, list) or not dataset:
        raise ValueError(f"Dataset must be a non-empty JSON list: {DATASET_PATH}")

    required_fields = {"id", "input", "expected_output"}

    for index, case in enumerate(dataset):
        if not isinstance(case, dict):
            raise ValueError(f"Dataset item at index {index} must be a JSON object.")

        missing_fields = required_fields - case.keys()
        if missing_fields:
            raise ValueError(
                f"Dataset item at index {index} is missing fields: "
                f"{sorted(missing_fields)}"
            )

    logger.info(
        "application_quality_dataset_loaded",
        dataset_path=str(DATASET_PATH),
        total_cases=len(dataset),
    )
    return dataset


# ============================================================
# RAG INITIALIZATION
# ============================================================

def initialize_rag() -> ConversationalRAG:
    """Initialize the RAG application and load the existing FAISS index."""

    if not FAISS_INDEX_PATH.exists():
        raise FileNotFoundError(f"FAISS index not found: {FAISS_INDEX_PATH}")

    rag = ConversationalRAG(session_id="application-quality-evaluation")
    rag.load_retriever_from_faiss(
        index_path=str(FAISS_INDEX_PATH),
        k=RETRIEVER_K,
        search_type="mmr",
        fetch_k=RETRIEVER_FETCH_K,
        lambda_mult=RETRIEVER_LAMBDA_MULT,
    )

    logger.info(
        "application_quality_rag_initialized",
        index_path=str(FAISS_INDEX_PATH),
    )
    return rag


# ============================================================
# RETRIEVAL CONTEXT
# ============================================================

def get_retrieval_context(
    rag: ConversationalRAG,
    question: str,
) -> list[str]:
    """Retrieve document text for the evaluation metrics."""

    documents = rag.retriever.invoke(question)
    context: list[str] = []

    for document in documents:
        if isinstance(document, str):
            text = document.strip()
        else:
            text = str(getattr(document, "page_content", "")).strip()

        if text:
            context.append(text)

    return context


# ============================================================
# ANSWER GENERATION
# ============================================================

def generate_answer(rag: ConversationalRAG, question: str) -> str:
    """Generate an answer using the application's RAG chain."""

    response = rag.invoke(question, chat_history=[])

    if isinstance(response, str):
        answer = response
    elif isinstance(response, dict):
        answer = (
            response.get("answer")
            or response.get("response")
            or response.get("output")
            or response.get("result")
        )
        if answer is None:
            raise ValueError(
                "RAG returned a dictionary without a recognized answer field. "
                f"Available keys: {list(response.keys())}"
            )
    else:
        answer = str(response)

    answer = str(answer).strip()
    if not answer:
        raise ValueError("RAG returned an empty answer.")

    return answer


# ============================================================
# METRIC EVALUATION
# ============================================================

def evaluate_metric(
    metric_name: str,
    metric: Any,
    test_case: LLMTestCase,
) -> dict[str, Any]:
    """Run one metric and capture its score, reason, or error."""

    start_time = time.perf_counter()

    try:
        metric.measure(test_case)

        score = getattr(metric, "score", None)
        reason = getattr(metric, "reason", None)

        if score is None:
            raise ValueError(f"Metric '{metric_name}' did not return a score.")

        score = float(score)
        passed = score >= METRIC_THRESHOLD

        result = {
            "score": score,
            "threshold": METRIC_THRESHOLD,
            "passed": passed,
            "reason": reason,
            "error": None,
            "duration_seconds": round(time.perf_counter() - start_time, 3),
        }

        logger.info(
            "application_quality_metric_completed",
            metric=metric_name,
            score=score,
            passed=passed,
        )
        return result

    except Exception as exc:
        logger.exception(
            "application_quality_metric_failed",
            metric=metric_name,
            error=str(exc),
        )
        return {
            "score": None,
            "threshold": METRIC_THRESHOLD,
            "passed": False,
            "reason": None,
            "error": str(exc),
            "duration_seconds": round(time.perf_counter() - start_time, 3),
        }


# ============================================================
# SINGLE-CASE EVALUATION
# ============================================================

def evaluate_case(
    case: dict[str, Any],
    rag: ConversationalRAG,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    """Generate and evaluate one application quality test case."""

    case_id = str(case["id"])
    question = str(case["input"])
    expected_output = str(case["expected_output"])

    logger.info("application_quality_case_started", case_id=case_id)
    case_start = time.perf_counter()

    result: dict[str, Any] = {
        "case_id": case_id,
        "input": question,
        "expected_output": expected_output,
        "actual_output": None,
        "retrieval_context": [],
        "metrics": {},
        "status": "error",
        "execution_error": None,
        "duration_seconds": None,
    }

    try:
        actual_answer = generate_answer(rag=rag, question=question)
        result["actual_output"] = actual_answer

        retrieval_context = get_retrieval_context(rag=rag, question=question)
        result["retrieval_context"] = retrieval_context

        test_case = LLMTestCase(
            input=question,
            actual_output=actual_answer,
            expected_output=expected_output,
            retrieval_context=retrieval_context,
            context=retrieval_context,
        )

        # Run metrics independently so one metric failure does not stop others.
        for metric_name, metric in metrics.items():
            result["metrics"][metric_name] = evaluate_metric(
                metric_name=metric_name,
                metric=metric,
                test_case=test_case,
            )

        metric_results = list(result["metrics"].values())
        has_metric_errors = any(item["error"] is not None for item in metric_results)
        all_metrics_passed = bool(metric_results) and all(
            item["passed"] and item["error"] is None for item in metric_results
        )

        if has_metric_errors:
            result["status"] = "error"
        elif all_metrics_passed:
            result["status"] = "passed"
        else:
            result["status"] = "failed"

    except Exception as exc:
        result["execution_error"] = str(exc)
        result["status"] = "error"
        logger.exception(
            "application_quality_case_failed",
            case_id=case_id,
            error=str(exc),
        )

    result["duration_seconds"] = round(time.perf_counter() - case_start, 3)

    logger.info(
        "application_quality_case_completed",
        case_id=case_id,
        status=result["status"],
        duration_seconds=result["duration_seconds"],
    )
    return result


# ============================================================
# SUMMARY
# ============================================================

def build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate overall and per-metric evaluation statistics."""

    total_cases = len(results)
    passed_cases = sum(result["status"] == "passed" for result in results)
    failed_cases = sum(result["status"] == "failed" for result in results)
    error_cases = sum(result["status"] == "error" for result in results)

    metric_names = sorted({
        metric_name
        for result in results
        for metric_name in result.get("metrics", {})
    })

    metric_summary: dict[str, Any] = {}

    for metric_name in metric_names:
        metric_results = [
            result["metrics"][metric_name]
            for result in results
            if metric_name in result.get("metrics", {})
        ]
        successful_results = [
            item
            for item in metric_results
            if item.get("error") is None and item.get("score") is not None
        ]

        scores = [item["score"] for item in successful_results]
        metric_passes = sum(item["passed"] for item in successful_results)
        metric_errors = sum(item.get("error") is not None for item in metric_results)

        metric_summary[metric_name] = {
            "average_score": round(sum(scores) / len(scores), 4) if scores else None,
            "passed_count": metric_passes,
            "evaluated_count": len(successful_results),
            "pass_rate": (
                round(metric_passes / len(successful_results), 4)
                if successful_results
                else None
            ),
            "error_count": metric_errors,
            "threshold": METRIC_THRESHOLD,
        }

    return {
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "error_cases": error_cases,
        "case_pass_rate": round(passed_cases / total_cases, 4) if total_cases else 0.0,
        "metric_summary": metric_summary,
    }


# ============================================================
# REPORT SAVING
# ============================================================

def save_report(
    results: list[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    """Save the complete evaluation report as JSON."""

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "evaluation_name": "Application Quality Evaluation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "judge_model": JUDGE_MODEL_NAME,
        "rag_index_path": str(FAISS_INDEX_PATH),
        "threshold": METRIC_THRESHOLD,
        "summary": summary,
        "results": results,
    }

    with REPORT_PATH.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=4, ensure_ascii=False)

    logger.info(
        "application_quality_report_saved",
        report_path=str(REPORT_PATH),
        total_cases=summary["total_cases"],
    )


# ============================================================
# CONSOLE SUMMARY
# ============================================================

def print_summary(summary: dict[str, Any]) -> None:
    """Print a readable evaluation summary to the terminal."""

    print("\n" + "=" * 60)
    print("APPLICATION QUALITY EVALUATION")
    print("=" * 60)
    print(f"Total cases:       {summary['total_cases']}")
    print(f"Passed cases:      {summary['passed_cases']}")
    print(f"Failed cases:      {summary['failed_cases']}")
    print(f"Cases with errors: {summary['error_cases']}")
    print(f"Case pass rate:    {summary['case_pass_rate']:.2%}")
    print("\nMetric summary:")

    for metric_name, stats in summary["metric_summary"].items():
        average = stats["average_score"]
        pass_rate = stats["pass_rate"]
        average_text = f"{average:.4f}" if average is not None else "N/A"
        pass_rate_text = f"{pass_rate:.2%}" if pass_rate is not None else "N/A"

        print(
            f"{metric_name:<22}"
            f"average={average_text:<8}"
            f"pass_rate={pass_rate_text:<8}"
            f"errors={stats['error_count']}"
        )

    print(f"\nJSON report: {REPORT_PATH}")
    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    """Run the full application quality evaluation."""

    logger.info("application_quality_evaluation_started")

    try:
        dataset = load_dataset()
        rag = initialize_rag()
        metrics = initialize_metrics()

        results: list[dict[str, Any]] = []
        for case in dataset:
            results.append(
                evaluate_case(case=case, rag=rag, metrics=metrics)
            )

        summary = build_summary(results)
        save_report(results=results, summary=summary)
        print_summary(summary)

        logger.info(
            "application_quality_evaluation_finished",
            total_cases=summary["total_cases"],
            passed_cases=summary["passed_cases"],
            failed_cases=summary["failed_cases"],
            error_cases=summary["error_cases"],
        )

    except Exception as exc:
        logger.exception(
            "application_quality_evaluation_aborted",
            error=str(exc),
        )
        raise


if __name__ == "__main__":
    main()
