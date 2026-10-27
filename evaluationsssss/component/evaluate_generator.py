
from deepeval import evaluate
from deepeval.metrics import (
    FaithfulnessMetric,
    AnswerRelevancyMetric,
)
from deepeval.test_case import LLMTestCase

from evaluation.adapters.project_adapter import ProjectAdapter


def evaluate_generator(
    cases: list[dict],
    judge_model,
) -> None:
    adapter = ProjectAdapter()
    metrics = [
        FaithfulnessMetric(
            threshold=0.90,
            model=judge_model,
        ),
        AnswerRelevancyMetric(
            threshold=0.80,
            model=judge_model,
        ),
    ]

    test_cases = []

    for case in cases:
        contexts = case["reference_contexts"]
        actual = adapter.generate(
            question=case["question"],
            contexts=contexts,
        )

        test_cases.append(
            LLMTestCase(
                input=case["question"],
                actual_output=actual,
                expected_output=case["expected_answer"],
                retrieval_context=contexts,
            )
        )

    evaluate(test_cases=test_cases, metrics=metrics)
