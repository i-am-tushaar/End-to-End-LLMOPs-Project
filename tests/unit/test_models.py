"""
Unit tests for multi_doc_chat/model/models.py.

Purpose:
    Verify that the Pydantic models validate input correctly and that
    PromptType contains the expected enum values.

Models tested:
    1. ChatAnswer: the answer text returned by the LLM (1 to 4096 characters).
    2. PromptType: an enum of the prompt templates used by the application.
    3. UploadResponse: the response sent after documents are uploaded.
    4. ChatRequest: the request body sent when a user asks a question.
    5. ChatResponse: the response body that carries the answer back.

How to read these tests:
    * Each test has a heading comment above it with a number, a title,
      and an objective, so you can see what is being checked at a glance.
    * Each test is split into short steps (create data, call, verify).
    * Tests that expect a failure use pytest.raises(ValidationError).
      Pydantic raises ValidationError when the input breaks a model rule.
"""

import pytest
from pydantic import ValidationError

from multi_doc_chat.model.models import (
    ChatAnswer,
    PromptType,
    UploadResponse,
    ChatRequest,
    ChatResponse,
)


# ## 1. ChatAnswer model tests


# Test 1: Accept a valid answer
# Objective: Verify that ChatAnswer accepts a normal answer
# and stores the text unchanged.
def test_chat_answer_accepts_valid_answer():
    """Verify that ChatAnswer accepts a valid answer that is not empty."""

    # Step 1: Create the model with a normal answer.
    result = ChatAnswer(answer="Hello, how can I help?")

    # Step 2: Verify that the text was stored as given.
    assert result.answer == "Hello, how can I help?"


# Test 2: Reject an empty answer
# Objective: Verify that an empty string is not accepted,
# because the answer must contain at least one character.
def test_chat_answer_rejects_empty_answer():
    """Verify that an empty answer is rejected."""

    # Step 1: Pass an empty string and expect a validation error.
    # ChatAnswer requires at least one character.
    with pytest.raises(ValidationError):
        ChatAnswer(answer="")


# Test 3: Accept the maximum length
# Objective: Verify that an answer of exactly 4096 characters is accepted.
# This is the boundary test: the longest allowed value must still pass.
def test_chat_answer_accepts_maximum_length():
    """Verify that an answer of exactly 4096 characters is accepted."""

    # Step 1: Build an answer with exactly 4096 characters.
    result = ChatAnswer(answer="a" * 4096)

    # Step 2: Verify that all 4096 characters were kept.
    assert len(result.answer) == 4096


# Test 4: Reject an answer over the maximum length
# Objective: Verify that an answer of 4097 characters is rejected.
# This is the other side of the boundary: one character too long must fail.
def test_chat_answer_rejects_answer_over_maximum_length():
    """Verify that answers longer than 4096 characters are rejected."""

    # Step 1: Pass 4097 characters and expect a validation error.
    # The model limits the answer to 4096 characters.
    with pytest.raises(ValidationError):
        ChatAnswer(answer="a" * 4097)


# Test 5: Require the answer field
# Objective: Verify that the answer field cannot be left out.
def test_chat_answer_requires_answer_field():
    """Verify that validation fails when the answer field is missing."""

    # Step 1: Create the model with no arguments and expect an error.
    with pytest.raises(ValidationError):
        ChatAnswer()


# ## 2. PromptType enum tests


# Test 6: Check the contextualize question value
# Objective: Verify that CONTEXTUALIZE_QUESTION maps to the string
# "contextualize_question", which other code relies on.
def test_prompt_type_contextualize_question_value():
    """Verify the expected value for contextualizing a question."""

    # Step 1: Compare the enum value with the expected string.
    assert (
        PromptType.CONTEXTUALIZE_QUESTION.value
        == "contextualize_question"
    )


# Test 7: Check the context QA value
# Objective: Verify that CONTEXT_QA maps to the string "context_qa".
def test_prompt_type_context_qa_value():
    """Verify the expected value for context based question answering."""

    # Step 1: Compare the enum value with the expected string.
    assert PromptType.CONTEXT_QA.value == "context_qa"


# Test 8: Convert a string into an enum member
# Objective: Verify that a valid string can be turned back into
# the matching PromptType member.
def test_prompt_type_accepts_valid_enum_member():
    """Verify that a valid string can be converted to a PromptType."""

    # Step 1: Convert the string into a PromptType.
    result = PromptType("context_qa")

    # Step 2: Verify that it is the expected enum member.
    assert result == PromptType.CONTEXT_QA


# Test 9: Reject an unknown value
# Objective: Verify that a string that is not in the enum
# raises a ValueError.
def test_prompt_type_rejects_invalid_value():
    """Verify that an unknown prompt type raises a ValueError."""

    # Step 1: Pass an unknown string and expect a ValueError.
    # Enums raise ValueError (not ValidationError) for unknown values.
    with pytest.raises(ValueError):
        PromptType("invalid_prompt_type")


# ## 3. UploadResponse model tests


# Test 10: Accept valid data
# Objective: Verify that UploadResponse stores all three fields
# when every field is supplied.
def test_upload_response_accepts_valid_data():
    """Verify that UploadResponse accepts all valid response fields."""

    # Step 1: Create the model with all fields.
    result = UploadResponse(
        session_id="session-123",
        indexed=True,
        message="Documents indexed successfully",
    )

    # Step 2: Verify that every field was stored correctly.
    assert result.session_id == "session-123"
    assert result.indexed is True
    assert result.message == "Documents indexed successfully"


# Test 11: Allow the message to be missing
# Objective: Verify that message is optional and defaults to None.
def test_upload_response_allows_optional_message_to_be_missing():
    """Verify that the optional message can be omitted."""

    # Step 1: Create the model without a message.
    result = UploadResponse(
        session_id="session-123",
        indexed=False,
    )

    # Step 2: Verify the default value.
    # The model defines message as optional, so its default is None.
    assert result.message is None


# Test 12: Require session_id
# Objective: Verify that session_id cannot be left out.
def test_upload_response_requires_session_id():
    """Verify that session_id is required."""

    # Step 1: Leave out session_id and expect a validation error.
    with pytest.raises(ValidationError):
        UploadResponse(indexed=True)


# Test 13: Require indexed
# Objective: Verify that indexed cannot be left out.
def test_upload_response_requires_indexed():
    """Verify that indexed is required."""

    # Step 1: Leave out indexed and expect a validation error.
    with pytest.raises(ValidationError):
        UploadResponse(session_id="session-123")


# Test 14: Reject an invalid boolean
# Objective: Verify that a string that cannot be read as true or false
# is rejected for the indexed field.
def test_upload_response_rejects_invalid_indexed_type():
    """Verify that an invalid string cannot be used as a boolean."""

    # Step 1: Pass a meaningless string and expect a validation error.
    # Pydantic can read strings such as "true" as booleans,
    # but it cannot read "not-a-boolean".
    with pytest.raises(ValidationError):
        UploadResponse(
            session_id="session-123",
            indexed="not-a-boolean",
        )


# ## 4. ChatRequest model tests


# Test 15: Accept valid data
# Objective: Verify that ChatRequest stores the session ID
# and the user's message.
def test_chat_request_accepts_valid_data():
    """Verify that ChatRequest accepts a session ID and message."""

    # Step 1: Create the model with both required fields.
    result = ChatRequest(
        session_id="session-123",
        message="Explain RAG",
    )

    # Step 2: Verify that both fields were stored correctly.
    assert result.session_id == "session-123"
    assert result.message == "Explain RAG"


# Test 16: Require session_id
# Objective: Verify that a request without a session ID is rejected.
def test_chat_request_requires_session_id():
    """Verify that session_id cannot be omitted."""

    # Step 1: Leave out session_id and expect a validation error.
    with pytest.raises(ValidationError):
        ChatRequest(message="Explain RAG")


# Test 17: Require message
# Objective: Verify that a request without a message is rejected.
def test_chat_request_requires_message():
    """Verify that message cannot be omitted."""

    # Step 1: Leave out message and expect a validation error.
    with pytest.raises(ValidationError):
        ChatRequest(session_id="session-123")


# Test 18: Reject a non string message
# Objective: Verify that a number is not accepted as the message.
def test_chat_request_rejects_non_string_message():
    """Verify that an integer cannot be used as the message."""

    # Step 1: Pass an integer and expect a validation error.
    # Pydantic does not silently convert an integer into a string.
    with pytest.raises(ValidationError):
        ChatRequest(
            session_id="session-123",
            message=123,
        )


# ## 5. ChatResponse model tests


# Test 19: Accept a valid answer
# Objective: Verify that ChatResponse stores a string answer unchanged.
def test_chat_response_accepts_valid_answer():
    """Verify that ChatResponse accepts a string answer."""

    # Step 1: Create the model with a string answer.
    result = ChatResponse(
        answer="RAG combines retrieval and generation."
    )

    # Step 2: Verify that the answer was stored as given.
    assert result.answer == "RAG combines retrieval and generation."


# Test 20: Require the answer field
# Objective: Verify that the answer field cannot be left out.
def test_chat_response_requires_answer():
    """Verify that the answer field is mandatory."""

    # Step 1: Create the model with no arguments and expect an error.
    with pytest.raises(ValidationError):
        ChatResponse()


# Test 21: Reject a non string answer
# Objective: Verify that a number is not accepted as the answer.
def test_chat_response_rejects_non_string_answer():
    """Verify that an integer cannot be used as the answer."""

    # Step 1: Pass an integer and expect a validation error.
    with pytest.raises(ValidationError):
        ChatResponse(answer=123)