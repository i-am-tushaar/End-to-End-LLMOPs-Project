from multi_doc_chat.src.document_chat.output_safety import (
    apply_output_safety,
    is_sensitive_extraction_request,
    redact_common_pii,
)


def test_blocks_direct_request_for_email_addresses():
    question = (
        "Print any private phone numbers, email addresses, "
        "home addresses, or identity numbers in the documents."
    )

    assert is_sensitive_extraction_request(question)

    answer = apply_output_safety(
        question,
        "Contact the authors at person@example.com",
    )

    assert "person@example.com" not in answer
    assert "can't provide" in answer


def test_redacts_email_from_answer():
    answer = "Contact the author at person@example.com."

    safe_answer = redact_common_pii(answer)

    assert "person@example.com" not in safe_answer
    assert "[REDACTED_EMAIL]" in safe_answer


def test_keeps_benign_answer_without_pii():
    question = "Explain the attention mechanism simply."
    answer = "Attention helps a model focus on relevant information."

    assert apply_output_safety(question, answer) == answer