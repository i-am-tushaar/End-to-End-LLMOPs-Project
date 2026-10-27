# Models Unit Test Results

## 1. Module Tested

- **Source:** `multi_doc_chat/model/models.py`
- **Test file:** `tests/unit/test_models.py`
- **Testing framework:** pytest
- **Test type:** Unit testing

## 2. Test Command

```bash
uv run pytest tests/unit/test_models.py -v
```

## 3. Test Summary

| Metric          | Result       |
| --------------- | -----------: |
| Total tests     |           21 |
| Passed          |           21 |
| Failed          |            0 |
| Execution time  | 0.18 seconds |
| Status          |   **PASSED** |

The test file has 21 test functions and none of them are parametrized, so each one runs once.

## 4. Test Coverage by Model

| Model            | Tests | What was verified                                                                                   |
| ---------------- | ----: | --------------------------------------------------------------------------------------------------- |
| `ChatAnswer`     |     5 | Valid answer, empty answer, maximum length boundary (4096), over the maximum (4097), and the required field |
| `PromptType`     |     4 | Both enum values, conversion from a valid string, and rejection of an unknown value                 |
| `UploadResponse` |     5 | Valid data, optional message, required `session_id`, required `indexed`, and an invalid boolean     |
| `ChatRequest`    |     4 | Valid data, required `session_id`, required `message`, and a non string message                     |
| `ChatResponse`   |     3 | Valid answer, required `answer`, and a non string answer                                            |
| **Total**        | **21** |                                                                                                    |

## 5. Detailed Test Results

All tests below passed.

### 5.1 ChatAnswer

- `test_chat_answer_accepts_valid_answer`: verifies that a normal answer is accepted and stored unchanged.
- `test_chat_answer_rejects_empty_answer`: verifies that an empty answer raises `ValidationError`.
- `test_chat_answer_accepts_maximum_length`: verifies that an answer of exactly 4096 characters is accepted.
- `test_chat_answer_rejects_answer_over_maximum_length`: verifies that an answer of 4097 characters raises `ValidationError`.
- `test_chat_answer_requires_answer_field`: verifies that leaving out `answer` raises `ValidationError`.

### 5.2 PromptType

- `test_prompt_type_contextualize_question_value`: verifies that `CONTEXTUALIZE_QUESTION` has the value `contextualize_question`.
- `test_prompt_type_context_qa_value`: verifies that `CONTEXT_QA` has the value `context_qa`.
- `test_prompt_type_accepts_valid_enum_member`: verifies that the string `context_qa` converts to `PromptType.CONTEXT_QA`.
- `test_prompt_type_rejects_invalid_value`: verifies that an unknown string raises `ValueError`.

### 5.3 UploadResponse

- `test_upload_response_accepts_valid_data`: verifies that `session_id`, `indexed`, and `message` are all stored correctly.
- `test_upload_response_allows_optional_message_to_be_missing`: verifies that `message` can be omitted and defaults to `None`.
- `test_upload_response_requires_session_id`: verifies that leaving out `session_id` raises `ValidationError`.
- `test_upload_response_requires_indexed`: verifies that leaving out `indexed` raises `ValidationError`.
- `test_upload_response_rejects_invalid_indexed_type`: verifies that a string that is not a valid boolean raises `ValidationError`.

### 5.4 ChatRequest

- `test_chat_request_accepts_valid_data`: verifies that `session_id` and `message` are stored correctly.
- `test_chat_request_requires_session_id`: verifies that leaving out `session_id` raises `ValidationError`.
- `test_chat_request_requires_message`: verifies that leaving out `message` raises `ValidationError`.
- `test_chat_request_rejects_non_string_message`: verifies that an integer message raises `ValidationError`.

### 5.5 ChatResponse

- `test_chat_response_accepts_valid_answer`: verifies that a string answer is stored unchanged.
- `test_chat_response_requires_answer`: verifies that leaving out `answer` raises `ValidationError`.
- `test_chat_response_rejects_non_string_answer`: verifies that an integer answer raises `ValidationError`.

## 6. Conclusion

All 21 unit tests passed successfully. The tested Pydantic models and the `PromptType` enum behaved as expected for the valid and invalid inputs covered by these tests.

**Limitation:** These tests check input validation only. They do not prove that the API endpoints that use these models return the right data in production, so those should also be checked with integration tests.