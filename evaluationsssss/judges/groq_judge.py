"""
groq_judge.py

LLM as a Judge using a free Groq model.

What it does:
    * Scores one answer from 1 to 5 against a rubric (single answer grading).
    * Compares two answers and picks a winner (pairwise grading).
    * Grades a list of answers and summarizes the results (batch grading).

Why it is built this way:
    * Temperature is 0, so the same input gives the same verdict.
    * The model writes its reasoning first, then the score, which gives
      more reliable scores than a score alone.
    * The pass or fail decision is made in Python, not by the model.
    * Pairwise grading runs twice with the answers swapped, to remove
      position bias (judges often favor the first answer).
    * Calls are spaced out and retried, to stay inside the Groq free tier
      limits (about 30 requests per minute).

Setup:
    * Put GROQ_API_KEY in your .env file or environment.
    * Free tier models change often. Check console.groq.com/docs/models
      if a model name stops working.

Quick start:
    judge = GroqJudge()
    result = judge.judge(question="What is RAG?", answer="...", context="...")
    print(result.score, result.passed, result.reasoning)
"""

from __future__ import annotations

import os
import time
from typing import Dict, Iterable, List, Literal, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from multi_doc_chat.exception.custom_exception import DocumentPortalException
from multi_doc_chat.logger import GLOBAL_LOGGER as log


# Best quality on the free tier. Use FAST_MODEL for quick runs, because it has
# a much higher daily request limit but is a weaker judge.
DEFAULT_MODEL = "openai/gpt-oss-120b"
FAST_MODEL = "openai/gpt-oss-20b"

# Default rubric for judging answers from a RAG system.
# Replace it with your own text to judge something else.
DEFAULT_RUBRIC = (
    "Score from 1 to 5:\n"
    "5 = Fully correct, complete, relevant, and grounded in the context.\n"
    "4 = Mostly correct and relevant, with only minor gaps.\n"
    "3 = Partly correct, but with a clear gap or a weakly supported claim.\n"
    "2 = Mostly incorrect, off topic, or largely unsupported.\n"
    "1 = Wrong, irrelevant, or contradicts the context."
)

# The prompts avoid curly braces on purpose, because the prompt template
# would treat them as variables. The word JSON is required by Groq json mode.
_SCORE_SYSTEM_PROMPT = (
    "You are a strict and fair evaluator of AI assistant answers.\n"
    "Rules:\n"
    "1. Judge only against the rubric. Do not reward length, style, or a "
    "confident tone.\n"
    "2. If context is provided, any claim that the context does not support "
    "lowers the score.\n"
    "3. If a reference answer is provided, treat it as the correct answer.\n"
    "4. Write your reasoning first, then give the score.\n"
    "Respond only with a JSON object with the keys reasoning (a short string) "
    "and score (an integer from 1 to 5)."
)

_PAIRWISE_SYSTEM_PROMPT = (
    "You are a strict and fair evaluator comparing two AI assistant answers "
    "to the same question.\n"
    "Rules:\n"
    "1. Pick the answer that is more correct, relevant, and complete.\n"
    "2. Do not prefer an answer because of its length, style, or position.\n"
    "3. If both answers are equally good or equally bad, answer tie.\n"
    "4. Write your reasoning first, then give the winner.\n"
    "Respond only with a JSON object with the keys reasoning (a short string) "
    "and winner (the string A, B, or tie)."
)


# ## Output schemas


class _ScoreOutput(BaseModel):
    """Raw structure the model must return when grading one answer."""

    reasoning: str = Field(description="Short explanation of the score.")
    score: int = Field(ge=1, le=5, description="Score from 1 to 5.")


class _PairwiseOutput(BaseModel):
    """Raw structure the model must return when comparing two answers."""

    reasoning: str = Field(description="Short explanation of the choice.")
    winner: Literal["A", "B", "tie"]


class JudgeResult(BaseModel):
    """Final result for one graded answer."""

    reasoning: str
    score: int
    passed: bool
    model: str


class PairwiseResult(BaseModel):
    """Final result for one comparison of two answers."""

    winner: Literal["A", "B", "tie"]
    consistent: bool = Field(
        description="False when the verdict changed after swapping positions."
    )
    reasoning: str


# ## Judge


class GroqJudge:
    """LLM as a Judge that uses a free Groq model to grade answers."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        rubric: str = DEFAULT_RUBRIC,
        pass_score: int = 4,
        min_interval: float = 2.0,
        max_attempts: int = 2,
        max_context_chars: int = 6000,
        api_key: Optional[str] = None,
    ):
        """
        Create a judge.

        Args:
            model_name: Groq model used as the judge.
            rubric: Text that explains how to score an answer.
            pass_score: Lowest score that counts as passed.
            min_interval: Minimum seconds between calls. 2.0 matches the
                free tier limit of about 30 requests per minute.
            max_attempts: Tries per call, which covers broken JSON replies.
            max_context_chars: Context longer than this is cut, to stay
                inside the free tier token limit.
            api_key: Groq key. Defaults to the GROQ_API_KEY variable.

        Raises:
            DocumentPortalException: If no API key is available.
        """
        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            raise DocumentPortalException(
                "GROQ_API_KEY is missing. Add it to your .env file.", None
            )

        self.model_name = model_name
        self.rubric = rubric
        self.pass_score = pass_score
        self.min_interval = min_interval
        self.max_attempts = max_attempts
        self.max_context_chars = max_context_chars
        self._last_call = 0.0  # time of the last call, used for spacing

        # Temperature 0 keeps verdicts stable. ChatGroq also retries
        # rate limit errors (HTTP 429) on its own with a short wait.
        llm = ChatGroq(
            model=model_name,
            api_key=key,
            temperature=0,
            max_tokens=512,
            max_retries=3,
        )

        # json_mode asks Groq for valid JSON, and the schema checks the fields.
        self._score_chain = (
            ChatPromptTemplate.from_messages(
                [
                    ("system", _SCORE_SYSTEM_PROMPT),
                    (
                        "human",
                        "Rubric:\n{rubric}\n\nQuestion:\n{question}\n\n"
                        "Retrieved context:\n{context}\n\n"
                        "Reference answer:\n{reference}\n\n"
                        "Answer to evaluate:\n{answer}",
                    ),
                ]
            )
            | llm.with_structured_output(_ScoreOutput, method="json_mode")
        )
        self._pairwise_chain = (
            ChatPromptTemplate.from_messages(
                [
                    ("system", _PAIRWISE_SYSTEM_PROMPT),
                    (
                        "human",
                        "Question:\n{question}\n\n"
                        "Answer A:\n{answer_a}\n\n"
                        "Answer B:\n{answer_b}",
                    ),
                ]
            )
            | llm.with_structured_output(_PairwiseOutput, method="json_mode")
        )
        log.info("GroqJudge initialized", model=model_name, pass_score=pass_score)

    # Internal helpers

    def _clip(self, text: Optional[str]) -> str:
        """Cut long text and return a placeholder when text is missing."""
        if not text:
            return "Not provided"
        if len(text) > self.max_context_chars:
            return text[: self.max_context_chars] + " [truncated]"
        return text

    def _call(self, chain, inputs: Dict[str, str]):
        """Call a chain with spacing between calls and a retry on failure."""
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_attempts + 1):
            # Wait so that calls stay under the free tier requests per minute.
            wait = self.min_interval - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()

            try:
                return chain.invoke(inputs)
            except Exception as e:  # network, rate limit, or invalid JSON
                last_error = e
                log.warning("Judge call failed", attempt=attempt, error=str(e))

        log.error("Judge call failed after all attempts", error=str(last_error))
        raise DocumentPortalException("Groq judge call failed", last_error) from last_error

    # Single answer grading

    def judge(
        self,
        question: str,
        answer: str,
        context: Optional[str] = None,
        reference: Optional[str] = None,
    ) -> JudgeResult:
        """
        Score one answer from 1 to 5.

        Args:
            question: The question that was asked.
            answer: The answer to grade.
            context: Retrieved text the answer should be based on (optional).
            reference: A known correct answer (optional).

        Returns:
            JudgeResult with the reasoning, the score, and whether it passed.

        Raises:
            ValueError: If the question or answer is empty.
            DocumentPortalException: If the Groq call fails.
        """
        if not question.strip() or not answer.strip():
            raise ValueError("question and answer must not be empty")

        out = self._call(
            self._score_chain,
            {
                "rubric": self.rubric,
                "question": question,
                "answer": answer,
                "context": self._clip(context),
                "reference": self._clip(reference),
            },
        )
        return JudgeResult(
            reasoning=out.reasoning,
            score=out.score,
            passed=out.score >= self.pass_score,  # decided in code, not by the LLM
            model=self.model_name,
        )

    # Pairwise grading

    def _pick(self, question: str, answer_a: str, answer_b: str) -> _PairwiseOutput:
        """Ask the judge which of two answers is better, in the given order."""
        return self._call(
            self._pairwise_chain,
            {"question": question, "answer_a": answer_a, "answer_b": answer_b},
        )

    def compare(
        self,
        question: str,
        answer_a: str,
        answer_b: str,
        swap_positions: bool = True,
    ) -> PairwiseResult:
        """
        Decide which of two answers is better.

        Args:
            question: The question that was asked.
            answer_a: The first answer.
            answer_b: The second answer.
            swap_positions: Run a second time with the answers swapped. If the
                two runs disagree, the winner is a tie. This removes position
                bias but uses two calls instead of one.

        Returns:
            PairwiseResult with the winner (A, B, or tie).

        Raises:
            ValueError: If an input is empty.
            DocumentPortalException: If the Groq call fails.
        """
        if not (question.strip() and answer_a.strip() and answer_b.strip()):
            raise ValueError("question and both answers must not be empty")

        first = self._pick(question, answer_a, answer_b)
        if not swap_positions:
            return PairwiseResult(
                winner=first.winner, consistent=True, reasoning=first.reasoning
            )

        # Second run with the order reversed, then map the winner back.
        second = self._pick(question, answer_b, answer_a)
        mapped = {"A": "B", "B": "A", "tie": "tie"}[second.winner]

        if first.winner == mapped:
            return PairwiseResult(
                winner=first.winner, consistent=True, reasoning=first.reasoning
            )
        return PairwiseResult(
            winner="tie",
            consistent=False,
            reasoning=f"Verdict changed after swapping positions. {first.reasoning}",
        )

    # Batch grading

    def judge_batch(
        self, items: Iterable[Dict[str, str]]
    ) -> List[Optional[JudgeResult]]:
        """
        Grade many answers one after another.

        Args:
            items: Dicts with the keys question and answer, and optionally
                context and reference.

        Returns:
            One entry per item. An entry is None when its call failed, so one
            bad item does not stop the whole run.
        """
        results: List[Optional[JudgeResult]] = []
        for index, item in enumerate(items):
            try:
                results.append(
                    self.judge(
                        question=item["question"],
                        answer=item["answer"],
                        context=item.get("context"),
                        reference=item.get("reference"),
                    )
                )
            except Exception as e:
                log.error("Skipping item", index=index, error=str(e))
                results.append(None)
        return results

    @staticmethod
    def summarize(results: List[Optional[JudgeResult]]) -> Dict[str, float]:
        """
        Summarize batch results.

        Returns:
            A dict with total, graded, failed_calls, mean_score, and pass_rate.
        """
        graded = [r for r in results if r is not None]
        count = len(graded)
        return {
            "total": len(results),
            "graded": count,
            "failed_calls": len(results) - count,
            "mean_score": round(sum(r.score for r in graded) / count, 2) if count else 0.0,
            "pass_rate": round(sum(r.passed for r in graded) / count, 2) if count else 0.0,
        }


if __name__ == "__main__":
    # Small demo. Run with: python -m multi_doc_chat.evaluation.groq_judge
    judge = GroqJudge()

    verdict = judge.judge(
        question="What does RAG do?",
        answer="RAG retrieves relevant documents to improve generated answers.",
        context="RAG retrieves relevant documents to improve generated answers.",
    )
    print("Single answer:", verdict.score, verdict.passed, verdict.reasoning)

    duel = judge.compare(
        question="What does RAG do?",
        answer_a="RAG retrieves documents to ground the answer.",
        answer_b="RAG is a type of database.",
    )
    print("Pairwise winner:", duel.winner, "consistent:", duel.consistent)
