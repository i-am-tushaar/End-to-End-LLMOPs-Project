# Regression Testing

## 1. Overview

Regression testing verifies that existing functionality continues to work after code changes, bug fixes, refactoring, dependency updates, or new features.

In this project, regression tests protect important behavior in the End-to-End LLMOps RAG application. They complement unit, integration, and API tests rather than replacing them.

## 2. Why Do We Need Regression Tests?

A change can fix one issue but accidentally break another feature that previously worked. Regression tests help detect these unintended side effects early.

For example, after modifying output-safety logic, the application should still:
- Block direct requests to extract sensitive personal information.
- Redact common personally identifiable information (PII) from generated answers.
- Allow benign questions and answers to work normally.

## 3. Unit Tests vs. Regression Tests

| Test type | Main purpose | Example in this project |
|---|---|---|
| Unit tests | Test a function or component in isolation. | Test email redaction in `tests/unit/test_output_safety.py`. |
| Regression tests | Protect important previously working behavior from breaking after future changes. | Recheck that sensitive-data requests are blocked in `tests/regression/test_safety_regression.py`. |
| Integration tests | Verify that multiple components work together. | Test document ingestion and retrieval-chain behavior. |
| API tests | Verify HTTP endpoints and API responses. | Test upload, chat, health, and Swagger endpoints. |

**Important:** The difference is primarily the testing objective, not simply the folder name. Regression tests may overlap with unit tests when the behavior is security- or reliability-critical.

## 4. Current Regression Test Structure

```text
tests/
├── unit/
│   ├── test_output_safety.py
│   └── test_retrieval.py
├── integration/
├── api/
└── regression/
    └── test_safety_regression.py
```

The exact contents of the other test folders may grow as the project evolves.

### `tests/unit/test_output_safety.py`

Tests output-safety functions individually, including:
- Detection of direct requests for private information.
- Redaction of email addresses.
- Preservation of benign answers without detected PII.

### `tests/regression/test_safety_regression.py`

Rechecks critical safety behavior across several input examples, including:
- Detection of requests for email addresses, phone numbers, Aadhaar numbers, and personal information.
- Returning the configured safe refusal for sensitive extraction requests.
- Redacting common email and numeric identifier patterns.
- Preserving benign answers.
- Avoiding a sensitive-request refusal for an unrelated educational question.

The regression tests are intentionally deterministic and do not require a live LLM call.

## 5. How to Run the Tests

Run only the safety regression tests:

```bash
uv run pytest tests/regression/test_safety_regression.py -v
```

Run every test currently inside the regression folder:

```bash
uv run pytest tests/regression/ -v
```

Run the complete test suite:

```bash
uv run pytest tests/ -v
```

The `-v` option displays individual test names and whether each test passed or failed.

## 6. Verified Test Results

On 28 October 2026, the project test output supplied during development showed:

| Test run | Result |
|---|---:|
| Safety regression tests | 12 passed |
| Full test suite | 166 passed, 10 warnings |

The 10 warnings were Pydantic deprecation warnings raised by LangChain tracing code. They did not cause test failures.

These are the results from that recorded run; rerun the commands after code changes to obtain the current results.

## 7. What Regression Tests Do Not Prove

Passing these tests does not prove that the entire RAG system is perfectly safe or that retrieval and generated answers are always correct.

In particular:
- Regex-based PII detection is a basic safeguard and may miss some sensitive information.
- Numeric redaction patterns can redact some non-sensitive numbers as well.
- The safety tests verify specific examples, not every possible phrasing or attack.
- Retrieval relevance, answer faithfulness, and grounding require separate tests and evaluation metrics.

## 8. When Should Regression Tests Be Updated?

Add or update regression tests when:
- A bug is discovered and fixed.
- Output-safety rules or prompts change.
- Retrieval or answer-generation behavior changes.
- A dependency upgrade could affect existing behavior.
- A failure in production or evaluation reveals a case that must not break again.

A useful practice is to turn every important reproducible bug into a regression test.

## 9. Recommended Workflow

1. Make a code change.
2. Run the relevant unit tests.
3. Run the regression tests.
4. Run integration and API tests when affected.
5. Run the complete suite before merging or pushing.
6. Review warnings and failures rather than ignoring them.

## 10. Summary

Regression testing is a safety net for future development. In this project, `tests/regression/test_safety_regression.py` complements `tests/unit/test_output_safety.py` by repeatedly checking critical privacy-protection behavior. Keep the regression folder as the suite grows, and add new tests when they protect important behavior not already covered adequately.
