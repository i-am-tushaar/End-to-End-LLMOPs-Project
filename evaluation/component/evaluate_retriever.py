
"""Evaluate FAISS retrieval quality with DeepEval contextual metrics."""

import json
from datetime import datetime, timezone
from pathlib import Path

from deepeval.metrics import (
    ContextualPrecisionMetric,
    ContextualRecallMetric,
)
from deepeval.test_case import LLMTestCase
from langchain_community.vectorstores import FAISS

from evaluation.judges.deepeval_groq_model import DeepEvalGroqModel
from multi_doc_chat.utils.model_loader import ModelLoader


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET_PATH = PROJECT_ROOT / "evaluation" / "datasets" / "retriever_eval.json"

# This is the candidate index inspected in the previous step.
INDEX_PATH = PROJECT_ROOT / "faiss_index" / "session_20261026_215230_88296173"

REPORT_DIR = PROJECT_ROOT / "evaluation" / "reports"

TOP_K = 3
FETCH_K = 10
LAMBDA_MULT = 0.5
THRESHOLD = 0.7


def load_dataset() -> list[dict]:
    """Load and validate the retriever evaluation dataset."""
    if not DATASET_PATH.is_file():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    with DATASET_PATH.open("r", encoding="utf-8") as file:
        dataset = json.load(file)

    if not isinstance(dataset, list) or not dataset:
        raise ValueError("The evaluation dataset must be a non-empty JSON list.")

    for item in dataset:
        for field in ("id", "input", "expected_output"):
            if not item.get(field):
                raise ValueError(
                    f"Dataset item is missing required field '{field}': {item}"
                )

    return dataset


def main() -> None:
    """Retrieve contexts, evaluate them, and save a JSON report."""
    dataset = load_dataset()

    if not INDEX_PATH.is_dir():
        raise FileNotFoundError(f"FAISS index not found: {INDEX_PATH}")

    # Load the same embedding configuration used by the application.
    embeddings = ModelLoader().load_embeddings()

    vectorstore = FAISS.load_local(
        str(INDEX_PATH),
        embeddings,
        index_name="index",
        allow_dangerous_deserialization=True,
    )

    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": TOP_K,
            "fetch_k": FETCH_K,
            "lambda_mult": LAMBDA_MULT,
        },
    )

    # Use the smaller judge model to reduce token consumption.
    judge = DeepEvalGroqModel(model_name="openai/gpt-oss-20b")

    precision_metric = ContextualPrecisionMetric(
        threshold=THRESHOLD,
        model=judge,
        include_reason=True,
    )
    recall_metric = ContextualRecallMetric(
        threshold=THRESHOLD,
        model=judge,
        include_reason=True,
    )

    results = []

    for item in dataset:
        question = item["input"]
        print(f"\nEvaluating {item['id']}: {question}")

        documents = retriever.invoke(question)
        contexts = [doc.page_content for doc in documents]

        if not contexts:
            print("WARNING: Retriever returned no documents.")

        # DeepEval requires an actual_output field. Since this is a
        # retriever-only evaluation, use the reference answer as a proxy.
        # These scores measure context quality against that reference;
        # they are not evaluations of a generated application answer.
        test_case = LLMTestCase(
            input=question,
            actual_output=item["expected_output"],
            expected_output=item["expected_output"],
            retrieval_context=contexts,
        )

        case_result = {
            "id": item["id"],
            "input": question,
            "retrieved_chunks": len(contexts),
            "retrieved_context": contexts,
        }

        for name, metric in (
            ("contextual_precision", precision_metric),
            ("contextual_recall", recall_metric),
        ):
            try:
                metric.measure(test_case)
                score = float(metric.score)

                case_result[name] = {
                    "score": score,
                    "passed": score >= THRESHOLD,
                    "reason": getattr(metric, "reason", None),
                }

                print(f"  {name}: {score:.3f}")

            except Exception as exc:
                case_result[name] = {
                    "error": f"{type(exc).__name__}: {exc}"
                }
                print(f"  {name} failed: {type(exc).__name__}: {exc}")

        results.append(case_result)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "index_path": str(INDEX_PATH.relative_to(PROJECT_ROOT)),
        "embedding_model": "Configured by ModelLoader",
        "judge_model": judge.get_model_name(),
        "top_k": TOP_K,
        "threshold": THRESHOLD,
        "results": results,
    }

    report_path = REPORT_DIR / "retriever_eval_results.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nReport saved to: {report_path}")

    for metric_name in ("contextual_precision", "contextual_recall"):
        scores = [
            result[metric_name]["score"]
            for result in results
            if metric_name in result and "score" in result[metric_name]
        ]

        if scores:
            print(f"Average {metric_name}: {sum(scores) / len(scores):.3f}")
        else:
            print(f"No successful scores for {metric_name}.")


if __name__ == "__main__":
    main()
