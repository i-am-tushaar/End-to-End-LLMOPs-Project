# API Test Plan

**Project:** End-to-End-LLMOPs-Project  
**Plan file:** `docs/API_TEST_PLAN.md`  
**Results report:** `docs/API_TEST_RESULTS.md`  
**Test file:** `tests/api/test_main.py`

## 1. Purpose

API tests verify that the FastAPI application exposes the expected endpoints, accepts valid requests, rejects invalid requests, and returns the correct HTTP status codes and response bodies.

This plan tracks the API tests for the project, explains what each endpoint test verifies, and records the status of the test suite.

The current API tests use FastAPI's `TestClient` and mocked dependencies. They test API behavior without starting a separate Uvicorn server or calling real embedding and LLM services.

## 2. API Test Plan

| Order | API test area | Endpoint(s) | What it proves | Dependencies | Status |
|---:|---|---|---|---|---|
| 1 | Health check | `GET /health` | The application returns a successful health response | FastAPI app | Done |
| 2 | Homepage | `GET /` | The homepage responds with HTML | FastAPI app and homepage file | Done |
| 3 | Swagger UI | `GET /docs` | Interactive API documentation is available | FastAPI app | Done |
| 4 | OpenAPI schema | `GET /openapi.json` | The generated API schema includes expected routes | FastAPI app | Done |
| 5 | Successful upload | `POST /upload` | A valid upload creates a session and returns the expected response | Mocked `ChatIngestor` | Done |
| 6 | Upload validation | `POST /upload` | A request without files returns HTTP 422 | FastAPI request validation | Done |
| 7 | Upload failure | `POST /upload` | An ingestion exception produces HTTP 500 | Mocked failing `ChatIngestor` | Done |
| 8 | Invalid chat session | `POST /chat` | An unknown session returns HTTP 400 | Session state | Done |
| 9 | Empty chat message | `POST /chat` | A blank message returns HTTP 400 | Valid session state | Done |
| 10 | Missing chat fields | `POST /chat` | Missing required fields return HTTP 422 | FastAPI request validation | Done |
| 11 | Successful chat | `POST /chat` | A valid question returns an answer and updates chat history | Mocked `ConversationalRAG` | Done |
| 12 | Chat failure | `POST /chat` | A RAG exception produces HTTP 500 | Mocked failing `ConversationalRAG` | Done |

**Status meanings:**

- **Not started:** The test has not yet been implemented or executed.
- **In progress:** The test is being developed or fixed.
- **Done:** The test has passed and the results have been recorded.

The statuses above reflect the previously reported successful execution. Re-run the tests after changes to confirm their current status.

## 3. Test Files and Results Reports

| Order | Test file | Results report |
|---:|---|---|
| 1–12 | `tests/api/test_main.py` | `docs/API_TEST_RESULTS.md` |

All 12 API tests are currently maintained in a single test module. Their individual test names and expected results are documented in the results report.

## 4. API Endpoints Covered

| Endpoint | Method | Tests | Purpose |
|---|---|---:|---|
| `/health` | GET | 1 | Checks application health |
| `/` | GET | 1 | Checks homepage HTML response |
| `/docs` | GET | 1 | Checks Swagger UI availability |
| `/openapi.json` | GET | 1 | Checks generated API schema |
| `/upload` | POST | 3 | Tests successful upload, missing files, and ingestion failure |
| `/chat` | POST | 5 | Tests session validation, message validation, successful chat, history, and RAG failure |
| **Total** | | **12** | |

## 5. Test Coverage by Area

| Area | Tests | What was verified |
|---|---:|---|
| Health and documentation | 4 | Health response, homepage, Swagger UI, and OpenAPI schema |
| Document upload | 3 | Successful upload, missing files, and ingestion failure |
| Chat request validation | 3 | Invalid session, empty message, and missing required fields |
| Chat success and failure | 2 | Answer and history updates, and RAG failure |
| **Total** | **12** | |

## 6. Expected HTTP Status Codes

| Status code | Meaning | Example in this project |
|---:|---|---|
| `200 OK` | The request succeeded | Health check, homepage, successful upload, and successful chat |
| `400 Bad Request` | The request cannot be processed because of invalid application state or input | Invalid session ID or empty chat message |
| `422 Unprocessable Entity` | FastAPI request validation failed | Missing upload files or required chat fields |
| `500 Internal Server Error` | An unexpected server-side operation failed | Simulated ingestion or RAG failure |

These status codes should match the application's actual route implementation and the assertions in the test file.

## 7. Testing Approach

### 7.1 FastAPI TestClient

`TestClient(main.app)` sends HTTP requests directly to the FastAPI application. A separate Uvicorn server is not required.

### 7.2 Mocking dependencies

The tests use `monkeypatch.setattr` to replace `ChatIngestor` and `ConversationalRAG` with fake implementations.

This allows the API routes to be tested without invoking the real ingestion pipeline, embedding providers, FAISS retrieval pipeline, or LLM.

### 7.3 Positive and negative testing

The suite verifies both successful requests and failure scenarios.

- **Positive tests:** Confirm that valid requests return expected responses.
- **Validation tests:** Confirm that missing or invalid inputs return the expected 4xx status codes.
- **Error-handling tests:** Confirm that simulated server-side failures return the expected 500 responses.
- **State tests:** Verify that sessions and chat history are updated as expected.

### 7.4 Isolation

The tests use in-memory session state. Clearing the session dictionary before each test is recommended so that tests remain independent and can safely be reordered.

## 8. Limitations and Future Improvements

The current suite verifies the API layer, not the complete production RAG workflow.

- **Mocked ingestion:** Successful upload tests do not prove that real files are embedded and indexed correctly.
- **Mocked RAG:** Successful chat tests do not prove that a real retriever and LLM generate a correct answer.
- **Session state:** The in-memory session dictionary does not test persistence across application restarts or multiple workers.
- **Authentication and security:** Add tests if authentication, authorization, rate limiting, or upload-size restrictions are introduced.
- **End-to-end behavior:** Use integration tests to verify actual document ingestion and retrieval, and end-to-end tests to verify the complete user journey.

These additional checks should be added when the relevant functionality exists in the application.

## 9. Workflow for API Testing

Follow these steps whenever the API or its dependencies change:

1. Update or add the relevant tests in `tests/api/test_main.py`.
2. Run the API test suite:

   ```bash
   uv run pytest tests/api/test_main.py -v
   ```

3. Review the output and investigate any failed tests.
4. Fix the application or test code as appropriate.
5. Re-run the tests and confirm that the suite passes.
6. Update `docs/API_TEST_RESULTS.md` with the latest execution results.
7. Update the status in Section 2 of this plan.
8. Commit the test changes, results report, and updated plan together.

Example commit:

```bash
git add tests/api/test_main.py docs/API_TEST_PLAN.md docs/API_TEST_RESULTS.md
git commit -m "test: document FastAPI endpoint test plan and results"
```

## 10. Run the Tests

### Run all API tests

```bash
uv run pytest tests/api/test_main.py -v
```

### Run all API tests with coverage

```bash
uv run pytest tests/api/test_main.py --cov=main --cov-report=term-missing
```

Adjust `--cov=main` if the application's actual import path differs.

### Run all API tests with an HTML coverage report

```bash
uv run pytest tests/api/test_main.py --cov=main --cov-report=html
```

Open `htmlcov/index.html` in a browser to inspect the coverage report.

### Run all project tests

```bash
uv run pytest -v
```

This runs all tests discovered by pytest, including unit, API, and integration tests, subject to the project's test discovery configuration.

## 11. Latest Recorded Results

| Metric | Result |
|---|---:|
| Test file | `tests/api/test_main.py` |
| Total tests | 12 |
| Passed | 12 |
| Failed | 0 |
| Execution time | 1.00 second |
| Status | **PASSED** |

Recorded output:

```text
12 passed in 1.00s
```

**Conclusion:** All 12 API tests passed in the recorded run. The suite verifies API responses, input validation, session handling, chat history updates, and simulated server errors. Integration tests are still needed to validate the real ingestion and RAG components working together.
