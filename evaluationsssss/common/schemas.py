
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvaluationCase:
    id: str
    question: str
    expected_answer: str | None = None
    relevant_chunk_ids: list[str] = field(default_factory=list)
    required_points: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    case_id: str
    level: str
    metrics: dict[str, float] = field(default_factory=dict)
    latency_seconds: float | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "level": self.level,
            "metrics": self.metrics,
            "latency_seconds": self.latency_seconds,
            "error": self.error,
        }
