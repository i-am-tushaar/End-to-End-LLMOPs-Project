
from dataclasses import dataclass
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVALUATION_ROOT = PROJECT_ROOT / "evaluation"
DATASET_DIR = EVALUATION_ROOT / "datasets"
REPORT_DIR = EVALUATION_ROOT / "reports"


@dataclass(frozen=True)
class EvaluationConfig:
    # Quality thresholds are initial targets, not achieved results.
    min_contextual_recall: float = 0.80
    min_contextual_precision: float = 0.80
    min_faithfulness: float = 0.90
    min_answer_relevancy: float = 0.80
    min_correctness: float = 0.80

    # Operational SLOs. Tune using measured baseline performance.
    max_latency_seconds: float = 10.0
    max_error_rate: float = 0.01

    @property
    def faiss_index_path(self) -> str:
        value = os.getenv("EVALUATION_FAISS_INDEX", "")
        if not value:
            raise ValueError(
                "Set EVALUATION_FAISS_INDEX to a valid FAISS index directory."
            )

        path = Path(value)
        if not path.is_absolute():
            path = PROJECT_ROOT / path

        if not path.exists():
            raise FileNotFoundError(f"FAISS index not found: {path}")

        return str(path)


CONFIG = EvaluationConfig()
