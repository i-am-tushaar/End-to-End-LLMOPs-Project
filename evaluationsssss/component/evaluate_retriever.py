
import json
from pathlib import Path

from evaluation.adapters.project_adapter import ProjectAdapter
from evaluation.component.metrics import retrieval_metrics
from evaluation.common.config import DATASET_DIR, REPORT_DIR


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def evaluate_retriever() -> list[dict]:
    adapter = ProjectAdapter()
    cases = load_jsonl(DATASET_DIR / "retriever.jsonl")
    results = []

    for case in cases:
        retrieved = adapter.retrieve(case["question"])
        retrieved_ids = [item["id"] for item in retrieved]

        metrics = retrieval_metrics(
            retrieved_ids=retrieved_ids,
            relevant_ids=case["relevant_chunk_ids"],
        )

        results.append({
            "case_id": case["id"],
            "level": "component",
            "component": "retriever",
            "metrics": metrics,
        })

    output = REPORT_DIR / "component" / "retriever.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    return results


if __name__ == "__main__":
    evaluate_retriever()
