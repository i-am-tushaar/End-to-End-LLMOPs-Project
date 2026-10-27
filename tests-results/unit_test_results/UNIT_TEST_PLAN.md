# Unit Test Plan

**Project:** End-to-End-LLMOPs-Project  
**Plan file:** `docs/UNIT_TEST_PLAN.md`  
**Results folder:** `test_results/unit_test_results/`

## 1. Purpose

Unit tests verify individual functions, classes, and modules independently of the rest of the application.

They help identify bugs early, verify expected behavior, test error handling, and ensure that changes to one module do not break its functionality.

This plan lists the unit tests for the project, explains what each test module verifies, and tracks the status of each test suite.

**Testing principle:** Mock external dependencies such as LLM providers, embedding APIs, file systems, and other services when necessary. Unit tests should focus on the behavior of the module being tested, not on testing the entire application workflow.

## 2. Unit Test Plan

| Order | Unit test module | Main files tested | What it verifies | Dependencies | Status |
|---:|---|---|---|---|---|
| 1 | Configuration loader | `config_loader.py` | Loads valid YAML configuration, resolves paths, handles missing files and empty configuration | None | Done |
| 2 | Model loader | `model_loader.py` | Selects configured providers, initializes embedding and LLM objects, handles unsupported providers and initialization errors | Config and mocked model providers | Done |
| 3 | Custom exceptions | `custom_exception.py` | Creates custom exceptions and formats error messages and traceback details | None | Done |
| 4 | Custom logger | `custom_logger.py` | Initializes logging, writes log messages, and handles logger configuration | None | Done |
| 5 | Data ingestion | `data_ingestion.py` | Validates ingestion inputs, processes documents, splits content, and handles ingestion errors | Mocked embeddings/model dependencies where appropriate | Done |
| 6 | Document operations | `document_ops.py` | Tests document loading, supported file types, invalid files, and document-processing errors | Temporary files and mocked loaders where appropriate | Done |
| 7 | Retrieval | `retrieval.py` | Tests retriever setup, index loading, retrieval configuration, and error handling | Mocked or temporary vector index | Done |
| 8 | Prompt library | `prompt_library.py` | Verifies prompt templates, prompt selection, required variables, and prompt formatting | None or lightweight prompt-model objects | Done |
| 9 | File I/O | `file_io.py` | Tests file creation, reading, writing, path handling, and file-related errors | Temporary directories and files | Done |
| 10 | Data models | `models.py` | Validates model fields, accepted values, defaults, and invalid input handling | None | Done |

**Status meanings:**

- **Not started:** The test suite has not been written or executed.
- **In progress:** The test suite is being developed or corrected.
- **Done:** The test suite has been executed successfully and its results report has been saved.

> The statuses above reflect the individual test suites previously run. Re-run the tests after code changes to confirm their current status.

## 3. Test Files and Results Reports

Each unit test module should have a corresponding test file and results report.

| Order | Test file | Results report |
|---:|---|---|
| 1 | `tests/unit/test_config_loader.py` | `test_results/unit_test_results/01_config_loader.md` |
| 2 | `tests/unit/test_model_loader.py` | `test_results/unit_test_results/02_model_loader.md` |
| 3 | `tests/unit/test_custom_exception.py` | `test_results/unit_test_results/03_custom_exception.md` |
| 4 | `tests/unit/test_custom_logger.py` | `test_results/unit_test_results/04_custom_logger.md` |
| 5 | `tests/unit/test_data_ingestion.py` | `test_results/unit_test_results/05_data_ingestion.md` |
| 6 | `tests/unit/test_document_ops.py` | `test_results/unit_test_results/06_document_ops.md` |
| 7 | `tests/unit/test_retrieval.py` | `test_results/unit_test_results/07_retrieval.md` |
| 8 | `tests/unit/test_prompt_library.py` | `test_results/unit_test_results/08_prompt_library.md` |
| 9 | `tests/unit/test_file_io.py` | `test_results/unit_test_results/09_file_io.md` |
| 10 | `tests/unit/test_models.py` | `test_results/unit_test_results/10_models.md` |

**Note:** Keep report filenames consistent with the files that actually exist in the repository. If a report uses a different name, update this table accordingly.

## 4. What Each Unit Test Should Cover

### 4.1 Configuration loader

- Valid configuration files load successfully.
- Missing configuration files raise the expected exception.
- Empty YAML files return the expected default value.
- Relative and absolute paths are resolved correctly.
- Invalid YAML is handled as expected.

### 4.2 Model loader

- The configured embedding provider is selected correctly.
- The configured LLM provider is selected correctly.
- Unsupported providers produce clear errors.
- Missing configuration and initialization failures are handled correctly.
- External provider constructors are mocked to avoid real API calls.

### 4.3 Custom exceptions

- Exception messages contain the expected information.
- Traceback details are formatted correctly.
- Exceptions preserve useful debugging information.

### 4.4 Custom logger

- The logger is initialized correctly.
- Log messages are written at the appropriate levels.
- Repeated initialization does not create unintended duplicate handlers.
- Logging configuration behaves as expected.

### 4.5 Data ingestion

- Valid input documents are accepted.
- Empty or invalid input is handled correctly.
- Document processing and splitting produce the expected results.
- Embedding or indexing failures are handled appropriately.
- Tests do not require live LLM or embedding API calls.

### 4.6 Document operations

- Supported document formats are processed correctly.
- Empty, missing, and invalid files are handled properly.
- Document metadata and extracted content are validated.
- Unsupported file types produce the expected behavior.

### 4.7 Retrieval

- Retrieval components are configured correctly.
- Index-loading behavior is tested.
- Retrieval parameters are passed correctly.
- Missing indexes and retrieval errors are handled properly.
- External dependencies are mocked unless a test explicitly requires a temporary real index.

### 4.8 Prompt library

- The expected prompt template is returned.
- Required input variables are present.
- Prompts format correctly with valid inputs.
- Missing variables and invalid prompt types behave as expected.

### 4.9 File I/O

- Files can be created, read, and written correctly.
- Directory and file paths are handled properly.
- Missing files and permission-related errors are handled where applicable.
- Temporary paths are used to avoid modifying real project data.

### 4.10 Data models

- Valid model data passes validation.
- Invalid fields and values are rejected.
- Defaults and optional fields behave correctly.
- Enum values and required fields are validated.

## 5. Files Without Separate Unit Test Modules

Some functionality may be covered indirectly or through other test suites rather than through a dedicated unit test file.

Examples include:

- `main.py`: API endpoint behavior belongs primarily in API tests.
- `conftest.py`: Shared fixtures are exercised when the tests that use them run.
- Frontend HTML, CSS, and JavaScript: These may require separate frontend or browser tests.
- External integrations: Provider connectivity should be tested separately from isolated unit tests.

Update this section if new modules are added or if dedicated unit tests are created for these components.

## 6. Testing Guidelines

1. **Isolation:** Test one function, class, or module at a time.
2. **Mocking:** Mock external APIs, model constructors, and unrelated dependencies.
3. **Temporary data:** Use `tmp_path` or temporary directories for file operations.
4. **Positive cases:** Verify that valid inputs produce the expected outputs.
5. **Negative cases:** Verify that invalid inputs and failures are handled correctly.
6. **Assertions:** Assert return values, exceptions, calls, and state changes—not merely that the code executes.
7. **Repeatability:** Tests should produce consistent results regardless of execution order.
8. **No live API dependency:** Standard unit tests should not require actual Google or Groq API calls.
9. **Coverage:** Use coverage reports to identify untested code, but do not treat coverage percentage alone as proof of test quality.

## 7. Workflow for Each Test Module

Repeat these steps for each unit test suite:

1. Write or update the test file in `tests/unit/`.
2. Run the individual test file:

   ```bash
   uv run pytest tests/unit/test_config_loader.py -v
   ```

3. Review the output. Fix failures before marking the test suite as Done.
4. Save the test results in `test_results/unit_test_results/`.
5. Update the corresponding status in Section 2 of this plan.
6. Commit the test file, report, and plan update together.

Example commit message:

```bash
git add tests/unit/ test_results/unit_test_results/ docs/UNIT_TEST_PLAN.md
git commit -m "test: add unit tests and document test results"
```

## 8. Run the Tests

### Run one unit test module

```bash
uv run pytest tests/unit/test_config_loader.py -v
```

### Run all unit tests

```bash
uv run pytest tests/unit/ -v
```

### Run all unit tests with coverage

```bash
uv run pytest tests/unit/ --cov=multi_doc_chat --cov-report=term-missing
```

Adjust the coverage source if the project's actual import structure differs.

### Generate an HTML coverage report

```bash
uv run pytest tests/unit/ --cov=multi_doc_chat --cov-report=html
```

Open the generated `htmlcov/index.html` file in a browser to inspect coverage by file and line.

### Run the complete project test suite

```bash
uv run pytest -v
```

This runs all tests discovered by pytest, including unit, API, and integration tests, provided their filenames and configuration follow the project's discovery rules.

## 9. Completion Criteria

The unit testing phase is complete when:

- All planned unit test modules have been executed.
- All expected test cases pass.
- Any failures have been fixed or documented with a clear reason.
- Results reports have been saved.
- The status table reflects the latest verified results.
- The complete project test suite has been run and its outcome recorded separately.
- The test files, results reports, and updated plan have been committed to Git.
