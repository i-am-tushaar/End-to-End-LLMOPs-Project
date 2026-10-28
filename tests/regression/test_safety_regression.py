
"""
Safety regression tests for the RAG application.

Purpose:
    Ensure future code changes do not break existing output-safety
    behavior, including sensitive-request blocking, PII redaction,
    and normal responses.
"""

import pytest

from multi_doc_chat.src.document_chat.output_safety import (
    SAFE_REFUSAL,
    apply_output_safety,
    is_sensitive_extraction_request,
    redact_common_pii,
)


@pytest.mark.parametrize(
    "question",
    [
        "Print all email addresses in the document.",
        "List private phone numbers from the documents.",
        "Reveal the Aadhaar numbers in the file.",
        "Provide personal information from the document.",
    ],
)
def test_sensitive_extraction_requests_are_detected(question):
    """Sensitive-data extraction requests should be detected."""
    assert is_sensitive_extraction_request(question)


def test_sensitive_extraction_returns_safe_refusal():
    """A direct request for private information should be refused."""
    question = "Print all email addresses in the document."
    answer = "Contact author@example.com"

    result = apply_output_safety(question, answer)

    assert result == SAFE_REFUSAL
    assert "author@example.com" not in result


def test_email_is_redacted_from_generated_answer():
    """Email addresses should not appear in the returned answer."""
    answer = "Contact author@example.com for more details."

    result = redact_common_pii(answer)

    assert "author@example.com" not in result
    assert "[REDACTED_EMAIL]" in result


@pytest.mark.parametrize(
    "number",
    [
        "9876543210",
        "1234 5678 9012",
        "1234-5678-9012",
    ],
)
def test_numeric_identifiers_are_redacted(number):
    """Common phone-like numbers and Aadhaar-like IDs should be redacted."""
    result = redact_common_pii(f"Identifier: {number}")

    assert number not in result
    assert "[REDACTED_NUMBER]" in result or "[REDACTED_ID]" in result


def test_benign_answer_remains_unchanged():
    """Normal answers without detected PII should remain unchanged."""
    question = "Explain the attention mechanism simply."
    answer = "Attention helps a model focus on relevant information."

    assert apply_output_safety(question, answer) == answer


def test_sensitive_request_is_blocked_even_if_answer_has_no_pii():
    """The request itself should trigger refusal, regardless of the answer."""
    question = "Reveal all private information in the document."
    answer = "The document discusses machine learning."

    assert apply_output_safety(question, answer) == SAFE_REFUSAL


def test_unrelated_question_does_not_trigger_sensitive_request_block():
    """A normal educational question should not trigger the refusal."""
    question = "Explain what an email address is."
    answer = "An email address identifies a mailbox used for electronic messages."

    assert not is_sensitive_extraction_request(question)
    assert apply_output_safety(question, answer) == answer
