# Model Loader — Unit Test Results

## 1. Overview

- **Module:** `multi_doc_chat/utils/model_loader.py`
- **Test file:** `tests/unit/test_model_loader.py`
- **Testing framework:** Pytest
- **Test type:** Unit testing
- **Components tested:** `ApiKeyManager` and `ModelLoader`

### Objective

Verify that API keys are loaded correctly from environment variables and ECS JSON secrets, missing or invalid configurations are handled appropriately, and embedding models and LLMs are initialized correctly using mocked dependencies.

## 2. Test Summary

| Test No. | Test Function | Expected Behavior | Status |
|---|---|---|---|
| 1 | `test_api_key_manager_loads_keys_from_environment` | Loads required keys from environment variables | PASSED |
| 2 | `test_api_key_manager_raises_error_when_keys_missing` | Raises `DocumentPortalException` when required keys are missing | PASSED |
| 3 | `test_api_key_manager_loads_keys_from_ecs_secret` | Loads keys from an ECS JSON secret | PASSED |
| 4 | `test_api_key_manager_handles_invalid_ecs_secret` | Handles invalid JSON and falls back to environment variables | PASSED |
| 5 | `test_api_key_manager_get_missing_key` | Raises `KeyError` when a requested key is unavailable | PASSED |
| 6 | `test_load_google_embeddings_success` | Initializes Google embeddings with the expected model and API key | PASSED |
| 7 | `test_load_huggingface_embeddings_success` | Initializes Hugging Face embeddings with the expected model | PASSED |
| 8 | `test_load_embeddings_unsupported_provider` | Raises `DocumentPortalException` for an unsupported embedding provider | PASSED |
| 9 | `test_load_embeddings_missing_provider_config` | Raises `DocumentPortalException` when embedding provider configuration is missing | PASSED |
| 10 | `test_load_google_llm_success` | Initializes Google Gemini with the expected configuration | PASSED |
| 11 | `test_load_groq_llm_success` | Initializes Groq with the expected configuration | PASSED |
| 12 | `test_load_llm_unsupported_provider` | Raises `DocumentPortalException` for an unsupported LLM provider | PASSED |
| 13 | `test_load_llm_missing_provider_config` | Raises `DocumentPortalException` when LLM provider configuration is missing | PASSED |

**Total tests:** 13  
**Passed:** 13  
**Failed:** 0  
**Skipped:** 0

## 3. Detailed Test Results

### A. ApiKeyManager Tests

#### Test 1: Load API Keys from Environment Variables

**Objective:** Verify that required API keys are loaded from environment variables when no ECS secret is available.

**Input:** Fake `GOOGLE_API_KEY` and `GROQ_API_KEY` environment variables.

**Expected result:** Both keys are retrieved with their expected values.

**Actual result:** Both assertions passed.

**Status:** PASSED

**Command:**

```bash
pytest tests/unit/test_model_loader.py::test_api_key_manager_loads_keys_from_environment -v
```

**Conclusion:** Environment-based API key loading works as expected.

---

#### Test 2: Handle Missing API Keys

**Objective:** Verify that initialization fails when both required API keys are missing.

**Input:** ECS secret and both API key environment variables removed.

**Expected result:** `DocumentPortalException` with a message containing `Missing API keys`.

**Actual result:** The expected exception was raised.

**Status:** PASSED

**Command:**

```bash
pytest tests/unit/test_model_loader.py::test_api_key_manager_raises_error_when_keys_missing -v
```

**Conclusion:** Missing required API keys are detected correctly.

---

#### Test 3: Load API Keys from ECS JSON Secrets

**Objective:** Verify that API keys are loaded from the ECS JSON secret.

**Input:** A valid JSON secret containing fake Google and Groq API keys, with individual environment variables removed.

**Expected result:** Both keys are retrieved from the ECS secret.

**Actual result:** Both assertions passed.

**Status:** PASSED

**Command:**

```bash
pytest tests/unit/test_model_loader.py::test_api_key_manager_loads_keys_from_ecs_secret -v
```

**Conclusion:** ECS secret loading works as expected.

---

#### Test 4: Handle Invalid ECS Secret JSON

**Objective:** Verify that invalid ECS JSON is handled safely and environment variables are used as a fallback.

**Input:** Malformed ECS JSON and valid fake API key environment variables.

**Expected result:** JSON parsing failure is handled, and both environment keys are loaded.

**Actual result:** Both assertions passed.

**Status:** PASSED

**Command:**

```bash
pytest tests/unit/test_model_loader.py::test_api_key_manager_handles_invalid_ecs_secret -v
```

**Conclusion:** The loader safely handles malformed ECS secrets and falls back to environment variables.

---

#### Test 5: Handle a Missing Requested API Key

**Objective:** Verify that requesting an unavailable API key raises a clear error.

**Input:** A request for `UNKNOWN_KEY`.

**Expected result:** `KeyError` with a message containing `API key 'UNKNOWN_KEY' is missing`.

**Actual result:** The expected exception was raised.

**Status:** PASSED

**Command:**

```bash
pytest tests/unit/test_model_loader.py::test_api_key_manager_get_missing_key -v
```

**Conclusion:** Requests for unavailable API keys are handled correctly.

### B. Embedding Model Loader Tests

#### Test 6: Initialize Google Embeddings

**Objective:** Verify that Google embeddings are initialized with the configured model and Google API key.

**Expected result:** The Google embedding constructor receives the expected model name and API key.

**Actual result:** The mock constructor was called with the expected arguments, and the returned object matched the expected mock.

**Status:** PASSED

**Command:**

```bash
pytest tests/unit/test_model_loader.py::test_load_google_embeddings_success -v
```

---

#### Test 7: Initialize Hugging Face Embeddings

**Objective:** Verify that Hugging Face embeddings are initialized with the configured model name.

**Expected result:** The Hugging Face constructor receives the expected `model_name`. No API key is requested.

**Actual result:** The mock constructor was called with the expected argument, and the returned object matched the expected mock.

**Status:** PASSED

**Command:**

```bash
pytest tests/unit/test_model_loader.py::test_load_huggingface_embeddings_success -v
```

---

#### Test 8: Handle an Unsupported Embedding Provider

**Objective:** Verify that an unsupported embedding provider raises the custom exception.

**Expected result:** `DocumentPortalException` with a message containing `Failed to load embeddings`.

**Actual result:** The expected exception was raised.

**Status:** PASSED

**Command:**

```bash
pytest tests/unit/test_model_loader.py::test_load_embeddings_unsupported_provider -v
```

---

#### Test 9: Handle Missing Embedding Provider Configuration

**Objective:** Verify that a provider absent from the embedding configuration is handled correctly.

**Expected result:** `DocumentPortalException` with a message containing `Failed to load embeddings`.

**Actual result:** The expected exception was raised.

**Status:** PASSED

**Command:**

```bash
pytest tests/unit/test_model_loader.py::test_load_embeddings_missing_provider_config -v
```

### C. LLM Loader Tests

#### Test 10: Initialize Google Gemini

**Objective:** Verify that Google Gemini is initialized using the configured model, API key, temperature, and output-token limit.

**Expected result:** The Google LLM constructor receives the expected configuration.

**Actual result:** The mock constructor was called with the expected arguments, and the returned object matched the expected mock.

**Status:** PASSED

**Command:**

```bash
pytest tests/unit/test_model_loader.py::test_load_google_llm_success -v
```

---

#### Test 11: Initialize Groq

**Objective:** Verify that Groq is initialized using the configured model, API key, temperature, and token limit.

**Expected result:** The Groq constructor receives the expected arguments, including `max_tokens`.

**Actual result:** The mock constructor was called with the expected arguments, and the returned object matched the expected mock.

**Status:** PASSED

**Command:**

```bash
pytest tests/unit/test_model_loader.py::test_load_groq_llm_success -v
```

---

#### Test 12: Handle an Unsupported LLM Provider

**Objective:** Verify that an unsupported LLM provider raises the custom exception.

**Expected result:** `DocumentPortalException` with a message containing `Failed to load LLM`.

**Actual result:** The expected exception was raised.

**Status:** PASSED

**Command:**

```bash
pytest tests/unit/test_model_loader.py::test_load_llm_unsupported_provider -v
```

---

#### Test 13: Handle Missing LLM Provider Configuration

**Objective:** Verify that an LLM provider absent from the configuration is handled correctly.

**Expected result:** `DocumentPortalException` with a message containing `Failed to load LLM`.

**Actual result:** The expected exception was raised.

**Status:** PASSED

**Command:**

```bash
pytest tests/unit/test_model_loader.py::test_load_llm_missing_provider_config -v
```

## 4. Combined Test Execution

**Command executed:**

```bash
pytest tests/unit/test_model_loader.py -v
```

**Actual output summary:**

```text
collected 13 items

13 passed, 12 warnings in 0.18s
```

All 13 tests passed in the combined run.

## 5. Warnings

The test run reported 12 `DeprecationWarning` messages originating from installed FastAPI and Starlette dependencies. These concern the deprecated use of `asyncio.iscoroutinefunction()`.

The warnings did not cause any test failures.

## 6. Testing Approach

- Used pytest to execute the unit tests.
- Used `monkeypatch` to control environment variables.
- Used `MagicMock` and mocked constructors to test model initialization without making real external API calls.
- Verified expected return objects and constructor arguments.
- Verified custom exception handling for unsupported providers and missing configuration.

## 7. Scope and Limitations

These tests cover API-key management, supported embedding and LLM initialization paths, and selected configuration errors.

They do not verify live Google or Groq API connectivity, actual embedding generation, real model inference, or every possible initialization failure.

## 8. Final Conclusion

All 13 `ApiKeyManager` and `ModelLoader` unit tests passed individually and in the combined test run.

The tests verify:

- Environment-variable API key loading.
- ECS JSON secret loading and invalid-secret fallback.
- Missing API key validation.
- Google and Hugging Face embedding initialization.
- Google Gemini and Groq LLM initialization.
- Unsupported provider handling.
- Missing provider configuration handling.

**Final status: 13 passed, 0 failed.**
