
"""
Evaluate the answer-generation quality of the end-to-end RAG pipeline.

Metrics:
- Faithfulness: Is the answer supported by retrieved context?
- Answer relevancy: Does the answer address the question?
- Correctness: Does the answer match the reference answer?

Run:
    uv run python -m evaluation.component.evaluate_generator
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
)
from deepeval.test_case import LLMTestCase

from evaluation.judges.deepeval_groq_model import DeepEvalGroqModel
from multi_doc_chat.src.document_chat.retrieval import ConversationalRAG


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "evaluation" / "datasets" / "generator_eval.json"
REPORT_PATH = PROJECT_ROOT / "evaluation" / "reports" / "generator_eval_results.json"

# Use the FAISS index containing the Attention Is All You Need paper.
FAISS_INDEX_PATH = (
    PROJECT_ROOT
    / "faiss_index"
    / "session_20261026_215230_88296173"
)

# Retrieval settings: keep consistent with the retriever evaluation.
TOP_K = 3
FETCH_K = 10
LAMBDA_MULT = 0.5


def load_dataset() -> list[dict]:
    """Load reference questions and answers from the evaluation dataset."""
    with DATASET_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def main() -> None:
    """Generate real RAG answers and evaluate them."""
    if not FAISS_INDEX_PATH.is_dir():
        raise FileNotFoundError(
            f"FAISS index not found: {FAISS_INDEX_PATH}"
        )

    dataset = load_dataset()
    judge = DeepEvalGroqModel(model_name="openai/gpt-oss-20b")

    # These metrics use the Groq judge to score answer quality.
    faithfulness_metric = FaithfulnessMetric(
        threshold=0.7,
        model=judge,
        include_reason=True,
    )
    relevancy_metric = AnswerRelevancyMetric(
        threshold=0.7,
        model=judge,
        include_reason=True,
    )

    results = []

    # Initialize the application once instead of reloading the LLM per question.
    rag = ConversationalRAG(session_id="generator-evaluation")
    rag.load_retriever_from_faiss(
        index_path=str(FAISS_INDEX_PATH),
        k=TOP_K,
        search_type="mmr",
        fetch_k=FETCH_K,
        lambda_mult=LAMBDA_MULT,
    )

    for item in dataset:
        test_id = item["id"]
        question = item["input"]
        expected_answer = item["expected_output"]

        print(f"\nEvaluating {test_id}: {question}")

        try:
            # Generate the actual answer through the real application.
            actual_answer = rag.invoke(question, chat_history=[])

            # Retrieve the supporting context used to evaluate faithfulness.
            retrieved_docs = rag.retriever.invoke(question)
            retrieval_context = [
                doc.page_content for doc in retrieved_docs
            ]

            test_case = LLMTestCase(
                input=question,
                actual_output=actual_answer,
                expected_output=expected_answer,
                retrieval_context=retrieval_context,
            )

            faithfulness_metric.measure(test_case)
            faithfulness_score = faithfulness_metric.score
            faithfulness_reason = faithfulness_metric.reason

            relevancy_metric.measure(test_case)
            relevancy_score = relevancy_metric.score
            relevancy_reason = relevancy_metric.reason

            result = {
                "id": test_id,
                "input": question,
                "expected_output": expected_answer,
                "actual_output": actual_answer,
                "faithfulness": {
                    "score": faithfulness_score,
                    "passed": faithfulness_metric.is_successful(),
                    "reason": faithfulness_reason,
                },
                "answer_relevancy": {
                    "score": relevancy_score,
                    "passed": relevancy_metric.is_successful(),
                    "reason": relevancy_reason,
                },
                "error": None,
            }

            print(f"Faithfulness: {faithfulness_score:.3f}")
            print(f"Answer relevancy: {relevancy_score:.3f}")

        except Exception as exc:
            result = {
                "id": test_id,
                "input": question,
                "expected_output": expected_answer,
                "actual_output": None,
                "error": str(exc),
            }
            print(f"FAILED: {exc}")

        results.append(result)

    # Calculate averages only from successfully scored cases.
    scored_results = [
        result for result in results
        if result.get("error") is None
    ]

    def average(metric_name: str) -> float | None:
        scores = [
            result[metric_name]["score"]
            for result in scored_results
        ]
        return round(sum(scores) / len(scores), 4) if scores else None

    report = {
        "evaluation_type": "generator",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": str(DATASET_PATH.relative_to(PROJECT_ROOT)),
        "faiss_index": str(FAISS_INDEX_PATH.relative_to(PROJECT_ROOT)),
        "total_cases": len(dataset),
        "successful_cases": len(scored_results),
        "failed_cases": len(results) - len(scored_results),
        "average_faithfulness": average("faithfulness"),
        "average_answer_relevancy": average("answer_relevancy"),
        "results": results,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    print("\n=== GENERATOR EVALUATION SUMMARY ===")
    print(f"Cases: {len(dataset)}")
    print(f"Successful: {len(scored_results)}")
    print(f"Failed: {len(results) - len(scored_results)}")
    print(f"Average faithfulness: {average('faithfulness')}")
    print(f"Average answer relevancy: {average('answer_relevancy')}")
    print(f"Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
