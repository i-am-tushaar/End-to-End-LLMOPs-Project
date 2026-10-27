
"""
Pipeline-Level RAG Triad Evaluation
===================================

This module evaluates the complete RAG pipeline using three metrics:

1. Contextual Relevancy:
   Checks whether the retrieved context is relevant to the question.

2. Faithfulness:
   Checks whether the generated answer is supported by the retrieved context.

3. Answer Relevancy:
   Checks whether the generated answer addresses the user's question.

The evaluation uses:
- Existing ConversationalRAG implementation
- Existing FAISS vector index
- DeepEval metrics
- A Groq-backed LLM judge

Outputs:
- evaluation/reports/rag_triad_results.json
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
)
from deepeval.test_case import LLMTestCase

from evaluation.judges.deepeval_groq_model import DeepEvalGroqModel
from multi_doc_chat.src.document_chat.retrieval import ConversationalRAG

# Reuse the centralized structured logger from the application.
from multi_doc_chat.logger.custom_logger import GLOBAL_LOGGER as logger


# -------------------------------------------------------------------
# 1. Project paths and configuration
# -------------------------------------------------------------------

# Resolve the project root independently of the current terminal folder.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Dataset containing questions and their expected reference answers.
DATASET_PATH = PROJECT_ROOT / "evaluation" / "datasets" / "rag_triad_eval.json"

# Existing FAISS index created by your RAG application.
FAISS_INDEX_PATH = (
    PROJECT_ROOT
    / "faiss_index"
    / "session_20261026_215230_88296173"
)

# JSON report containing the individual scores and evaluation reasons.
REPORT_PATH = (
    PROJECT_ROOT
    / "evaluation"
    / "reports"
    / "rag_triad_results.json"
)

# Retrieval settings consistent with the existing generator evaluation.
TOP_K = 3
FETCH_K = 10
LAMBDA_MULT = 0.5

# Minimum score required for a metric to pass.
METRIC_THRESHOLD = 0.7

# Use the smaller judge model already tested in your environment.
JUDGE_MODEL_NAME = "openai/gpt-oss-20b"


# -------------------------------------------------------------------
# 2. Load the evaluation dataset
# -------------------------------------------------------------------

def load_dataset() -> list[dict[str, Any]]:
    """Load and validate the RAG Triad evaluation questions."""

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Evaluation dataset not found: {DATASET_PATH}"
        )

    with DATASET_PATH.open("r", encoding="utf-8") as file:
        dataset = json.load(file)

    if not isinstance(dataset, list) or not dataset:
        raise ValueError(
            "The RAG Triad dataset must be a non-empty JSON list."
        )

    # Validate required fields before making API calls.
    required_fields = {"id", "input", "expected_output"}

    for index, item in enumerate(dataset):
        if not isinstance(item, dict):
            raise ValueError(
                f"Dataset item {index} must be a JSON object."
            )

        missing_fields = required_fields - item.keys()

        if missing_fields:
            raise ValueError(
                f"Dataset item {index} is missing fields: "
                f"{sorted(missing_fields)}"
            )

    logger.info(
        "evaluation_dataset_loaded",
        total_cases=len(dataset),
    )
    return dataset


# -------------------------------------------------------------------
# 3. Initialize the RAG application and evaluation judge
# -------------------------------------------------------------------

def initialize_rag() -> ConversationalRAG:
    """
    Initialize the real RAG application and load its FAISS retriever.

    This ensures the evaluation tests the existing application rather
    than a separate or mocked implementation.
    """

    if not FAISS_INDEX_PATH.exists():
        raise FileNotFoundError(
            f"FAISS index not found: {FAISS_INDEX_PATH}"
        )

    rag = ConversationalRAG(session_id="rag-triad-evaluation")

    rag.load_retriever_from_faiss(
        index_path=str(FAISS_INDEX_PATH),
        k=TOP_K,
        search_type="mmr",
        fetch_k=FETCH_K,
        lambda_mult=LAMBDA_MULT,
    )

    logger.info("rag_application_initialized")
    return rag


def initialize_metrics() -> dict[str, Any]:
    """
    Create the three RAG Triad metrics using the same LLM judge.

    A shared judge configuration keeps the evaluation setup
    consistent across all three metrics.
    """

    judge = DeepEvalGroqModel(model_name=JUDGE_MODEL_NAME)

    return {
        "contextual_relevancy": ContextualRelevancyMetric(
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
        "answer_relevancy": AnswerRelevancyMetric(
            threshold=METRIC_THRESHOLD,
            model=judge,
            include_reason=True,
            async_mode=False,
        ),
    }


# -------------------------------------------------------------------
# 4. Run all three metrics for one question
# -------------------------------------------------------------------

def evaluate_case(
    item: dict[str, Any],
    rag: ConversationalRAG,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    """
    Generate an answer, collect retrieval context, and evaluate it.

    Each metric is handled independently so an error in one metric
    does not prevent the remaining metrics from being attempted.
    """

    question = item["input"]
    case_id = item["id"]

    logger.info(
        "rag_triad_case_started",
        case_id=case_id,
        question=question,
    )

    result: dict[str, Any] = {
        "id": case_id,
        "input": question,
        "expected_output": item["expected_output"],
        "actual_output": None,
        "retrieved_context_count": 0,
        "metrics": {},
        "errors": [],
    }

    # Generate the answer using the actual application.
    try:
        actual_answer = rag.invoke(
            question,
            chat_history=[],
        )

        result["actual_output"] = actual_answer

    except Exception as exc:
        error_message = f"Answer generation failed: {exc}"
        result["errors"].append(error_message)

        logger.exception(
            "rag_triad_generation_failed",
            case_id=case_id,
            error=str(exc),
        )
        return result

    # Retrieve the documents used as evidence for evaluation.
    try:
        retrieved_docs = rag.retriever.invoke(question)

        retrieval_context = [
            doc.page_content
            for doc in retrieved_docs
            if getattr(doc, "page_content", "").strip()
        ]

        result["retrieved_context_count"] = len(retrieval_context)

        if not retrieval_context:
            raise ValueError(
                "The retriever returned no usable document context."
            )

    except Exception as exc:
        error_message = f"Context retrieval failed: {exc}"
        result["errors"].append(error_message)

        logger.exception(
            "rag_triad_context_retrieval_failed",
            case_id=case_id,
            error=str(exc),
        )
        return result

    # DeepEval compares the answer and context using an LLMTestCase.
    test_case = LLMTestCase(
        input=question,
        actual_output=actual_answer,
        expected_output=item["expected_output"],
        retrieval_context=retrieval_context,
    )

    # Measure contextual relevancy, faithfulness, and answer relevancy.
    for metric_name, metric in metrics.items():
        try:
            metric.measure(test_case)

            result["metrics"][metric_name] = {
                "score": metric.score,
                "passed": metric.is_successful(),
                "reason": metric.reason,
            }

            logger.info(
                "rag_triad_metric_completed",
                case_id=case_id,
                metric=metric_name,
                score=metric.score,
                passed=metric.is_successful(),
            )

        except Exception as exc:
            # Preserve the failure in the report instead of hiding it.
            error_message = (
                f"{metric_name} evaluation failed: {exc}"
            )

            result["metrics"][metric_name] = {
                "score": None,
                "passed": False,
                "reason": None,
                "error": str(exc),
            }

            result["errors"].append(error_message)

            logger.exception(
                "rag_triad_metric_failed",
                case_id=case_id,
                metric=metric_name,
                error=str(exc),
            )

    return result


# -------------------------------------------------------------------
# 5. Calculate aggregate scores and save the report
# -------------------------------------------------------------------

def calculate_average(
    results: list[dict[str, Any]],
    metric_name: str,
) -> float | None:
    """
    Average the available scores for one metric.

    Failed metric calls are excluded from the average, but remain
    recorded in the individual case results.
    """

    scores = [
        result["metrics"][metric_name]["score"]
        for result in results
        if result["metrics"].get(metric_name, {}).get("score")
        is not None
    ]

    if not scores:
        return None

    return round(sum(scores) / len(scores), 4)


def save_report(
    dataset: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> None:
    """Save detailed results and summary metrics to a JSON report."""

    metric_names = [
        "contextual_relevancy",
        "faithfulness",
        "answer_relevancy",
    ]

    summary = {}

    for metric_name in metric_names:
        metric_results = [
            result["metrics"][metric_name]
            for result in results
            if metric_name in result["metrics"]
        ]

        valid_scores = [
            item["score"]
            for item in metric_results
            if item.get("score") is not None
        ]

        summary[metric_name] = {
            "average_score": calculate_average(results, metric_name),
            "successful_evaluations": len(valid_scores),
            "failed_evaluations": (
                len(dataset) - len(valid_scores)
            ),
            "passed_cases": sum(
                1
                for item in metric_results
                if item.get("passed") is True
            ),
        }

    # A case is successful only if all three metrics have scores
    # and no errors occurred during generation or evaluation.
    successful_cases = sum(
        1
        for result in results
        if not result["errors"]
        and all(
            result["metrics"].get(name, {}).get("score") is not None
            for name in metric_names
        )
    )

    report = {
        "evaluation_type": "pipeline_level_rag_triad",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": str(DATASET_PATH.relative_to(PROJECT_ROOT)),
        "faiss_index": str(FAISS_INDEX_PATH.relative_to(PROJECT_ROOT)),
        "judge_model": JUDGE_MODEL_NAME,
        "threshold": METRIC_THRESHOLD,
        "total_cases": len(dataset),
        "successful_cases": successful_cases,
        "failed_cases": len(dataset) - successful_cases,
        "summary": summary,
        "results": results,
    }

    # Create the reports directory if it does not exist.
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with REPORT_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False,
        )

    logger.info(
        "rag_triad_report_saved",
        report_path=str(REPORT_PATH),
    )


# -------------------------------------------------------------------
# 6. Main entry point
# -------------------------------------------------------------------

def main() -> None:
    """Execute the complete pipeline-level RAG Triad evaluation."""

    dataset = load_dataset()
    rag = initialize_rag()
    metrics = initialize_metrics()

    results = []

    for item in dataset:
        result = evaluate_case(item, rag, metrics)
        results.append(result)

    save_report(dataset, results)

    # Print a readable summary in the terminal.
    print("\n" + "=" * 55)
    print("RAG TRIAD EVALUATION SUMMARY")
    print("=" * 55)

    for result in results:
        print(
            f"{result['id']}: "
            f"{'SUCCESS' if not result['errors'] else 'ERROR'}"
        )

    print(f"Total cases: {len(dataset)}")
    print(
        "Successful cases: "
        f"{sum(1 for r in results if not r['errors'])}"
    )

    for metric_name in (
        "contextual_relevancy",
        "faithfulness",
        "answer_relevancy",
    ):
        average = calculate_average(results, metric_name)
        formatted_average = (
            f"{average:.3f}" if average is not None else "N/A"
        )
        print(f"Average {metric_name}: {formatted_average}")

    print(f"\nReport: {REPORT_PATH}")


if __name__ == "__main__":
    main()
