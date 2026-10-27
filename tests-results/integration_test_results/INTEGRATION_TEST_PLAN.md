# Integration Test Plan

**Project:** End-to-End-LLMOPs-Project\
**Plan file:** `docs/INTEGRATION_TEST_PLAN.md`\
**Results folder:** `test_results/integration_test_results/`

## 1. Purpose

Unit tests check each module on its own. Integration tests check that the modules work together. This plan lists the integration tests for the project, in the order they should be written, and tracks the status of each one.

Integration tests are named by flow, not by file. One test can involve several source files.

## 2. Test Plan

| Order | Integration test           | Files involved                                                                                         | What it proves                                                                          | Depends on                       | Status      |
| ----: | -------------------------- | ------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------- | -------------------------------- | ----------- |
|     1 | Document ingestion         | `data_ingestion.py`, `file_io.py`, `document_ops.py`, `model_loader.py`                                 | An uploaded file becomes a FAISS index and a retriever                                  | None                             | Done        |
|     2 | Retrieval chain            | `retrieval.py` (`ConversationalRAG`), `prompt_library.py`, `model_loader.py`, and the index from test 1 | The saved index loads from disk and the chain returns an answer                         | Test 1 (needs an index on disk)  | Not started |
|     3 | Chat with history          | `retrieval.py`, `prompt_library.py`, `models.py` (`PromptType`)                                        | A follow up question uses earlier messages (the contextualize question step)            | Test 2                           | Not started |
|     4 | API upload then chat       | `main.py`, plus everything above                                                                       | `/upload` followed by `/chat` works with a real session ID, without mocks               | Tests 1 to 3                     | Not started |
|     5 | Config and model loading   | `config_loader.py`, `model_loader.py`                                                                  | The real `config.yaml` loads and the configured embedding and LLM objects are created   | None                             | Not started |

## 3. Test Files and Reports

Each integration test has one test file and one results report.

| Order | Test file                                                  | Results report                                                          |
| ----: | ---------------------------------------------------------- | ----------------------------------------------------------------------- |
|     1 | `tests/integration/test_data_ingestion_integration.py`     | `test_results/integration_test_results/01_document_ingestion.md`        |
|     2 | `tests/integration/test_retrieval_chain_integration.py`    | `test_results/integration_test_results/02_retrieval_chain.md`           |
|     3 | `tests/integration/test_chat_history_integration.py`       | `test_results/integration_test_results/03_chat_with_history.md`         |
|     4 | `tests/integration/test_api_upload_chat_integration.py`    | `test_results/integration_test_results/04_api_upload_to_chat.md`        |
|     5 | `tests/integration/test_config_model_integration.py`       | `test_results/integration_test_results/05_config_and_model_loading.md`  |

## 4. How the Tests Connect

- **Test 2** depends on test 1. Build the index in a fixture, then load it with `load_retriever_from_faiss`.
- **Test 3** exercises `prompt_library.py`, so a separate test for that file is not needed.
- **Test 4** is the closest to real use. The existing API unit tests mock `ChatIngestor` and `ConversationalRAG`, and this test removes those mocks.
- **Test 5** is independent, so it can be written at any time.

## 5. Files Without Their Own Integration Test

`custom_exception.py`, `custom_logger.py`, and `models.py` are used by every flow above. They are covered whenever those flows run, and the unit tests already cover them directly.

## 6. Cautions

- **LLM calls:** tests 2, 3, and 4 call an LLM. Use a fake or stub LLM for most runs, and keep one small test with the real LLM marked `@pytest.mark.slow`, so normal runs stay fast and free.
- **File types:** test 1 only covers `.txt`. If `document_ops.py` has separate loaders for PDF, DOCX, and TXT, add a small test that loads one real file of each type.
- **Test order:** tests 2, 3, and 4 should not depend on each other's leftover files. Each test should build its own index in a temporary folder (`tmp_path`).

## 7. Workflow for Each Test

Repeat these steps for every row in the plan, in order:

1. Write the test file in `tests/integration/`, using the heading and step comment style of test 1.
2. Run the test:

    ```bash
    uv run pytest tests/integration/<test_file>.py -v
    ```

3. Write the results report in `test_results/integration_test_results/`.
4. Change the Status in section 2 of this plan to **Done**.
5. Commit the test file, the report, and the updated plan together.

Example commit message:

```bash
git commit -m "feat: add integration test for retrieval chain with pytest and FAISS, with results report"
```

## 8. Run the Tests

Run one integration test:

```bash
uv run pytest tests/integration/test_data_ingestion_integration.py -v
```

Run all integration tests:

```bash
uv run pytest tests/integration/ -v
```

Run only tests marked as integration:

```bash
uv run pytest -m integration -v
```
