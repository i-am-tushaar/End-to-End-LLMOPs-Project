# API Unit Test Results

## 1. Overview

- **Module tested:** `main.py` (FastAPI application)
- **Test file:** `tests/api/test_main.py`
- **Report file:** `docs/API_TEST_RESULTS.md`
- **Testing framework:** pytest
- **Test client:** FastAPI `TestClient` (no separate Uvicorn server is needed)
- **Test type:** Unit testing of API endpoints with mocked dependencies

## 2. Test Execution

Command:

```bash
uv run pytest tests/api/test_main.py -v
```

Result:

| Metric          |       Result |
| --------------- | -----------: |
| Total tests     |           12 |
| Passed          |           12 |
| Failed          |            0 |
| Execution time  | 1.00 seconds |
| Status          |   **PASSED** |

Observed result:

```text
12 passed in 1.00s
```

The test file has 12 test functions and none of them are parametrized, so each one runs once.

## 3. Endpoints Covered

| Endpoint        | Method | Tests | Purpose                                                  |
| --------------- | ------ | ----: | -------------------------------------------------------- |
| `/health`       | GET    |     1 | Confirms that the service is running                     |
| `/`             | GET    |     1 | Serves the homepage as HTML                              |
| `/docs`         | GET    |     1 | Serves the Swagger UI documentation                      |
| `/openapi.json` | GET    |     1 | Serves the generated OpenAPI schema                      |
| `/upload`       | POST   |     3 | Uploads documents and creates a chat session             |
| `/chat`         | POST   |     5 | Answers a question using the session's retriever and history |
| **Total**       |        | **12** |                                                         |

## 4. Test Coverage by Area

| Area                         | Tests | What was verified                                                                  |
| ---------------------------- | ----: | ---------------------------------------------------------------------------------- |
| Health and documentation     |     4 | Health response, HTML homepage, Swagger UI, and routes listed in the OpenAPI schema |
| Document upload              |     3 | Successful upload, missing files (422), and ingestion failure (500)                |
| Chat request validation      |     3 | Invalid session (400), empty message (400), and missing fields (422)               |
| Chat success and failure     |     2 | Answer returned and history saved, and RAG failure (500)                           |
| **Total**                    | **12** |                                                                                   |

## 5. Detailed Test Cases

### 5.1 Health and documentation

**Test 1: `test_health_returns_success`**

- **Request:** `GET /health`
- **Expected:** status code 200 and the body `{"status": "ok"}`.

**Test 2: `test_homepage_returns_html`**

- **Request:** `GET /`
- **Expected:** status code 200 and a `text/html` content type.

**Test 3: `test_swagger_docs_are_available`**

- **Request:** `GET /docs`
- **Expected:** status code 200 and a `text/html` content type, because Swagger UI is an HTML page.

**Test 4: `test_openapi_schema_contains_api_routes`**

- **Request:** `GET /openapi.json`
- **Expected:** status code 200, and the `paths` section of the schema contains `/health`, `/upload`, and `/chat`.

### 5.2 Document upload

**Test 5: `test_upload_successfully_creates_session`**

- **Mocked:** `ChatIngestor` is replaced with a fake class, so the real ingestion pipeline does not run.
- **Request:** `POST /upload` with one file, `notes.txt`, containing `Sample document`.
- **Expected response:** status code 200, `session_id` equal to `test-session-123`, `indexed` equal to `true`, and `message` equal to `Indexing complete with MMR`.
- **Checks made inside the fake class:**
    - Session specific directories are enabled (`use_session_dirs` is `True`).
    - Exactly one uploaded file is passed on, named `notes.txt`, and its content can be read.
    - The retrieval settings are `search_type` equal to `mmr`, `fetch_k` equal to 20, and `lambda_mult` equal to 0.5.
- **State check:** the new session starts with an empty chat history (`SESSIONS["test-session-123"] == []`).

**Test 6: `test_upload_without_files_returns_validation_error`**

- **Request:** `POST /upload` with no files attached.
- **Expected:** HTTP 422 (Unprocessable Entity), and the response contains a `detail` field. FastAPI rejects the request during input validation.

**Test 7: `test_upload_ingestion_failure_returns_server_error`**

- **Mocked:** `ChatIngestor` is replaced with a fake class that raises `RuntimeError("Simulated ingestion failure")`.
- **Request:** `POST /upload` with one valid file.
- **Expected:** HTTP 500, and the `detail` message contains `Upload failed`.

### 5.3 Chat request validation

**Test 8: `test_chat_with_invalid_session_returns_bad_request`**

- **Request:** `POST /chat` with the session ID `unknown-session`, which was never created.
- **Expected:** HTTP 400 (Bad Request), and the `detail` message contains `Invalid or expired session_id`.

**Test 9: `test_chat_with_empty_message_returns_bad_request`**

- **Setup:** a valid session is created first, so the request reaches the message check.
- **Request:** `POST /chat` with a message that contains only spaces.
- **Expected:** HTTP 400 (Bad Request), and the `detail` message is exactly `Message cannot be empty`.

**Test 10: `test_chat_missing_required_fields_returns_validation_error`**

- **Request:** `POST /chat` with an empty JSON object.
- **Expected:** HTTP 422 (Unprocessable Entity), and the response contains a `detail` field. `ChatRequest` requires both `session_id` and `message`.

### 5.4 Chat success and failure

**Test 11: `test_chat_success_saves_answer_and_history`**

- **Setup:** the session already holds two earlier messages (a user question and an assistant answer).
- **Mocked:** `ConversationalRAG` is replaced with a fake class, so no real retriever or LLM is used.
- **Request:** `POST /chat` with the message `Summarize the document`.
- **Expected response:** status code 200 and the body `{"answer": "The document explains software testing."}`.
- **Checks made inside the fake class:**
    - The retriever is loaded from `faiss_index/<session_id>` with `search_type` equal to `mmr`, `fetch_k` equal to 20, and `lambda_mult` equal to 0.5.
    - The current question reaches `invoke()`.
    - The two earlier messages are passed to `invoke()` as chat history.
- **State check:** the new user message and the generated answer are saved at the end of the session history, in that order.

**Test 12: `test_chat_rag_failure_returns_server_error`**

- **Setup:** a valid session with an empty history.
- **Mocked:** `ConversationalRAG` is replaced with a fake class whose `invoke()` raises `RuntimeError("Simulated RAG failure")`.
- **Request:** `POST /chat` with the message `Explain the document`.
- **Expected:** HTTP 500, and the `detail` message contains `Chat failed`.

## 6. Testing Approach

- **Test client:** `TestClient(main.app)` sends requests straight to the application, so no server has to be started.
- **Mocking:** `monkeypatch.setattr` replaces `ChatIngestor` and `ConversationalRAG` for the duration of one test. This keeps the tests fast and avoids real embeddings, FAISS indexes, and LLM calls.
- **Assertions inside fake classes:** the fakes also check the arguments the API passes to them, so the tests confirm both the HTTP response and how the API talks to its dependencies.
- **Error paths:** both 4xx errors (400 and 422) and 5xx errors (500) are exercised, along with the matching error messages.

## 7. Conclusion

All 12 tests passed. The suite covers all six routes in the application and checks successful responses, input validation errors, and server errors for the upload and chat endpoints.

**Limitations:**

- The ingestion pipeline and the RAG chain are mocked. These tests do not prove that real uploads, embeddings, FAISS persistence, or LLM answers work in production, so they should also be checked with integration and end to end tests.
- The tests share the in memory `main.SESSIONS` dictionary and reuse the session ID `test-session-123`. This works with the current test order, but clearing `SESSIONS` in a fixture before each test would make the tests safer to reorder or run in parallel.

## 8. Re-run the Tests

Run the API tests:

```bash
uv run pytest tests/api/test_main.py -v
```

Run all unit tests:

```bash
uv run pytest tests/unit/ -v
```

Run all unit tests with coverage reporting:

```bash
uv run pytest tests/unit/ --cov=multi_doc_chat --cov-report=term-missing
```