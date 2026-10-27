
from typing import Protocol, Any


class EvaluationAdapter(Protocol):
    def retrieve(self, question: str) -> list[dict[str, Any]]:
        """Return ranked chunks with stable IDs and text."""
        ...

    def generate(
        self, question: str, contexts: list[str]
    ) -> str:
        """Generate an answer from explicitly supplied contexts."""
        ...

    def answer(self, question: str) -> dict[str, Any]:
        """Run the complete RAG pipeline."""
        ...
