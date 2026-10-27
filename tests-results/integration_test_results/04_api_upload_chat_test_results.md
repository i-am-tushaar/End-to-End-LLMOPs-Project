# Integration Test Results: API Upload and Chat

## 1. Overview

- **Project:** End-to-End-LLMOPs-Project
- **Components tested:** FastAPI routes in `main.py`, `ChatIngestor` in `multi_doc_chat/src/document_ingestion/data_ingestion.py`, and `ConversationalRAG` in `multi_doc_chat/src/document_chat/retrieval.py`
- **Test file:** `tests/integration/04_test_api_upload_chat.py`
- **Report file:** `test_results/integration_test_results/04_api_upload_chat_test_results.md`
- **Testing framework:** pytest
- **Test type:** Integration testing

## 2. Test Execution

Command:

```bash
uv run pytest tests/integration/04_test_api_upload_chat.py -v
```

Result:

| Metric | Result |
|---|---|
| Total tests | 1 |
| Passed | 1 |
| Failed | 0 |
| Execution time | 0.57 seconds |
| Warnings | 2 |
| Status | PASSED |

Observed result:

```text
1 passed, 2 warnings in 0.57s
```

## 3. Purpose

Verify that the FastAPI application supports the complete document-upload-and-chat workflow.

The test uploads a TXT document through `POST /upload`, verifies successful indexing and the returned session ID, sends a question through `POST /chat`, and checks the response and updated conversation history.

The test integrates the API routes with document ingestion, FAISS index persistence, and the conversational RAG chain using stubbed embeddings and an LLM.

## 4. What Was Tested for Real and What Was Replaced

| Part of the pipeline | Status |
|---|---|
| FastAPI `POST /upload` endpoint | Real implementation |
| FastAPI `POST /chat` endpoint | Real implementation |
| Multipart file upload | Real implementation |
| `FastAPIFileAdapter` | Real implementation |
| `ChatIngestor` | Real implementation |
| Saving and splitting the uploaded document | Real implementation |
| FAISS index creation and saving | Real implementation |
| Session ID returned by the upload endpoint | Real implementation |
| Loading the saved FAISS index | Real implementation |
| `ConversationalRAG` initialization and LCEL chain invocation | Real implementation |
| Conversation history updates in `main.SESSIONS` | Real implementation |
| Model loader | Replaced by the `stub_model_loader` fixture |
| Embeddings | Replaced by stub embeddings |
| LLM answer generation | Replaced by the stub LLM |
| Data and FAISS storage | Isolated using temporary directories |

## 5. Test Case

**Integration Test 4: `test_api_upload_then_chat`**

- **Objective:** Verify that a document can be uploaded and indexed through the API and subsequently queried through the chat endpoint using the returned session ID.
- **Input:** An in-memory TXT file named `lakshya_guide.txt` containing information about Lakshya AI.
- **Setup:** FastAPI `TestClient`, temporary storage directories, cleared session history, and the `stub_model_loader` fixture.
- **Action:** Upload the document, retrieve the generated session ID, submit a question through `/chat`, and verify the response and conversation history.

| Step | What happens | Expected result |
|---:|---|---|
| 1 | Prepare a sample TXT document | The document contains known information about Lakshya AI |
| 2 | Send the file to `POST /upload` | The API returns HTTP 200 |
| 3 | Verify the upload response | `indexed` is `true` and a session ID is returned |
| 4 | Check the FAISS index files | `index.faiss` and `index.pkl` exist |
| 5 | Check session initialization | The session exists with empty chat history |
| 6 | Send a question to `POST /chat` | The API returns HTTP 200 |
| 7 | Verify the chat response | The response contains a non-empty answer |
| 8 | Verify conversation history | The user question and assistant answer are stored in the session |

## 6. Verification Points

1. The `/upload` endpoint returns HTTP 200.
2. The upload response contains a valid session ID.
3. The response confirms that indexing completed.
4. The `index.faiss` file exists in the session index folder.
5. The `index.pkl` file exists in the session index folder.
6. The session is initialized in `main.SESSIONS`.
7. The `/chat` endpoint returns HTTP 200 for the valid session.
8. The chat response contains a non-empty answer.
9. The conversation history stores the user's question.
10. The conversation history stores the corresponding assistant answer.

## 7. Conclusion

**Status: PASSED.**

The integration test successfully exercised the complete API workflow: document upload, ingestion, FAISS index creation, session initialization, chat request processing, and conversation history updates.

The test confirms that the real FastAPI endpoints work together with the ingestion and RAG components under the configured test environment.

**Limitations:**

- The embedding model is replaced by stub embeddings, so real Google or Hugging Face embedding providers are not tested.
- The LLM is stubbed and returns `"stubbed answer"`, so the test does not verify the correctness, relevance, or semantic quality of generated answers.
- Only one TXT document is tested. PDF, DOCX, multiple-file, and large-document scenarios are not covered.
- The test does not validate concurrent sessions, session expiration, or multi-turn answer quality.
- Two Pydantic deprecation warnings originate from LangChain tracing. They did not affect the test result.

## 8. Re-run the Test

Run this integration test:

```bash
uv run pytest tests/integration/04_test_api_upload_chat.py -v
```

Run all integration tests:

```bash
uv run pytest tests/integration/ -v
```

Run all tests:

```bash
uv run pytest -v
```
