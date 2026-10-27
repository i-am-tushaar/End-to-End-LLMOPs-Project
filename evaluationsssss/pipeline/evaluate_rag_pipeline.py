
import json
import time
from pathlib import Path

from deepeval import evaluate
from deepeval.metrics import (
    FaithfulnessMetric,
    AnswerRelevancyMetric,
    ContextualRelevancyMetric,
)
from deepeval.test_case import LLMTestCase

from evaluation.adapters.project_adapter import ProjectAdapter
from evaluation.common.config import DATASET_DIR, REPORT_DIR


def evaluate_pipeline(cases: list[dict], judge_model) -> list[dict]:
    adapter = ProjectAdapter()

    metrics = [
        FaithfulnessMetric(threshold=0.90, model=judge_model),
        AnswerRelevancyMetric(threshold=0.80, model=judge_model),
        ContextualRelevancyMetric(
            threshold=0.80, model=judge_model
        ),
    ]

    test_cases = []
    operational_results = []

    for case in cases:
        start = time.perf_counter()

        try:
            output = adapter.answer(case["question"])
            elapsed = time.perf_counter() - start

            answer = output["answer"]
            contexts = output["contexts"]

            test_cases.append(
                LLMTestCase(
                    input=case["question"],
                    actual_output=answer,
                    expected_output=case["expected_answer"],
                    retrieval_context=contexts,
                )
            )

            operational_results.append({
                "case_id": case["id"],
                "latency_seconds": elapsed,
                "error": None,
            })

        except Exception as exc:
            operational_results.append({
                "case_id": case["id"],
                "latency_seconds": time.perf_counter() - start,
                "error": f"{type(exc).__name__}: {exc}",
            })

    # Evaluate successful cases. If none succeeded, still save
    # the operational report instead of calling evaluate().
    if test_cases:
        evaluate(test_cases=test_cases, metrics=metrics)

    report = REPORT_DIR / "pipeline" / "operational.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(operational_results, indent=2),
        encoding="utf-8",
    )

    return operational_results
