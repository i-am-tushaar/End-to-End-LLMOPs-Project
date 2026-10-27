# Integration Test Results: Chat with History

## 1. Overview

- **Project:** End-to-End-LLMOPs-Project
- **Component tested:** `ConversationalRAG` in `multi_doc_chat/src/document_chat/retrieval.py` and `PromptType` in `multi_doc_chat/model/models.py`
- **Test file:** `tests/integration/03_test_chat_with_history.py`
- **Report file:** `test_results/integration_test_results/03_chat_with_history_test_results.md`
- **Testing framework:** pytest
- **Test type:** Integration testing

## 2. Test Execution

Command:

```bash
uv run pytest tests/integration/03_test_chat_with_history.py -v
```

Result:

| Metric | Result |
|---|---|
| Total tests | 1 |
| Passed | 1 |
| Failed | 0 |
| Execution time | 0.38 seconds |
| Warnings | 2 |
| Status | PASSED |

Observed result:

```text
1 passed, 2 warnings in 0.38s
```

## 3. Purpose

Verify that `ConversationalRAG` loads a saved FAISS index, builds the LangChain Expression Language (LCEL) chain, accepts previous conversation messages, and returns a non-empty answer for a follow-up question.

The test covers document ingestion, FAISS index creation and loading, and invocation of the conversational RAG chain with chat history using the stub LLM.

## 4. What Was Tested for Real and What Was Replaced

| Part of the pipeline | Status |
|---|---|
| `ChatIngestor` and FAISS index creation | Real implementation |
| Saving the uploaded file to temporary storage | Real implementation |
| Loading and splitting the document | Real implementation |
| FAISS index creation and saving | Real implementation |
| Loading the saved FAISS index | Real implementation |
| LCEL chain construction and invocation | Real implementation |
| Passing `HumanMessage` and `AIMessage` as chat history | Real implementation |
| Model loader | Replaced by the `stub_model_loader` fixture |
| Embeddings | Replaced by stub embeddings |
| LLM answer generation | Replaced by the stub LLM |
| Project `data` and `faiss_index` folders | Replaced by temporary folders (`tmp_path`) |

## 5. Test Case

**Integration Test 3: `test_chat_with_history_accepts_follow_up_question`**

- **Objective:** Verify that `ConversationalRAG` accepts previous conversation messages and processes a follow-up question.
- **Input:** An in-memory text file named `project_guide.txt` containing information about Lakshya AI.
- **Setup:** A `ChatIngestor` using temporary `data` and `faiss_index` folders, with the session ID `chat_history_test_session`.
- **Chat history:** A previous human question, `"What is the project called?"`, and an AI response, `"The project is called Lakshya AI."`
- **Action:** Ingest the document, load the saved index through `ConversationalRAG`, provide chat history, and ask `"What does it help students do?"`

| Step | What happens | Expected result |
|---:|---|---|
| 1 | Prepare a sample TXT document | The document contains information about Lakshya AI |
| 2 | Initialize `ChatIngestor` | Temporary folders isolate the test data |
| 3 | Run `built_retriver()` | The document is saved, split, and indexed |
| 4 | Check the FAISS index files | `index.faiss` and `index.pkl` exist |
| 5 | Initialize `ConversationalRAG` | The RAG component loads successfully |
| 6 | Load the saved FAISS index | The retriever is created and the LCEL chain is built |
| 7 | Prepare chat history | Previous human and AI messages are supplied |
| 8 | Invoke the chain with a follow-up question | The chain accepts the chat history and processes the question |
| 9 | Verify the answer | A non-empty string is returned |

## 6. Verification Points

1. `index.faiss` exists in the temporary session index folder.
2. `index.pkl` exists in the temporary session index folder.
3. The saved FAISS index loads successfully.
4. The retriever and LCEL chain initialize successfully.
5. Previous conversation messages are passed through the `chat_history` argument.
6. The follow-up question is processed without an exception.
7. `rag.chain` is not `None`.
8. `rag.invoke()` returns a non-empty string.

## 7. Conclusion

**Status: PASSED.**

The integration test successfully created and loaded a FAISS index, initialized the conversational RAG chain, supplied previous conversation messages, and processed a follow-up question. The chain returned a non-empty answer using the stub LLM.

**Limitations:**

- The embedding model is replaced by stub embeddings, so this test does not verify real Google or Hugging Face embedding providers.
- The LLM is stubbed and always returns `"stubbed answer"`. Therefore, the test does not verify answer quality or prove that the answer semantically depends on the chat history.
- Only one TXT document is used. PDF, DOCX, multiple-file, and large-document scenarios are not covered.
- The test does not validate API endpoints such as `/upload` and `/chat`.
- Two Pydantic deprecation warnings originate from LangChain tracing. They did not affect the test result.

## 8. Re-run the Test

Run this integration test:

```bash
uv run pytest tests/integration/03_test_chat_with_history.py -v
```

Run all integration tests:

```bash
uv run pytest tests/integration/ -v
```

Run all tests:

```bash
uv run pytest -v
```