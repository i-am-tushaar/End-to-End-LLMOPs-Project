# Model Loader — Unit Test Results

## 1. Overview

- **Module:** `multi_doc_chat/utils/model_loader.py`
- **Test file:** `tests/unit/test_model_loader.py`
- **Testing framework:** Pytest
- **Test type:** Unit testing
- **Component tested:** `ApiKeyManager`

### Objective

Verify that API keys are loaded correctly from environment variables and ECS JSON secrets, missing keys are handled appropriately, and invalid ECS secret JSON falls back to environment variables.

## 2. Test Summary

| Test No. | Test Function | Expected Behavior | Status |
|---|---|---|---|
| 1 | `test_api_key_manager_loads_keys_from_environment` | Loads required keys from environment variables | PASSED |
| 2 | `test_api_key_manager_raises_error_when_keys_missing` | Raises `DocumentPortalException` when required keys are missing | PASSED |
| 3 | `test_api_key_manager_loads_keys_from_ecs_secret` | Loads keys from an ECS JSON secret | PASSED |
| 4 | `test_api_key_manager_handles_invalid_ecs_secret` | Handles invalid JSON and falls back to environment variables | PASSED |
| 5 | `test_api_key_manager_get_missing_key` | Raises `KeyError` when a requested key is unavailable | PASSED |

**Total tests:** 5  
**Passed:** 5  
**Failed:** 0

## 3. Detailed Test Results

### Test 1: Load API Keys from Environment Variables

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

### Test 2: Handle Missing API Keys

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

### Test 3: Load API Keys from ECS JSON Secrets

**Objective:** Verify that API keys are loaded from the ECS JSON secret.

**Input:** A valid JSON secret containing fake Google and Groq API keys, with the individual environment variables removed.

**Expected result:** Both keys are retrieved from the ECS secret.

**Actual result:** Both assertions passed.

**Status:** PASSED

**Command:**
```bash
pytest tests/unit/test_model_loader.py::test_api_key_manager_loads_keys_from_ecs_secret -v
```

**Conclusion:** ECS secret loading works as expected.

---

### Test 4: Handle Invalid ECS Secret JSON

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

### Test 5: Handle a Missing Requested API Key

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

## 4. Combined Test Execution

**Command executed:**
```bash
pytest tests/unit/test_model_loader.py -v
```

**Actual output summary:**
```text
5 passed, 12 warnings in 0.09s
```

All five tests passed in the combined run.

## 5. Warnings

The test run reported 12 `DeprecationWarning` messages originating from FastAPI and Starlette dependencies. They concern the deprecated use of `asyncio.iscoroutinefunction()` in Python 3.14.6.

These warnings did not cause any test failures.

## 6. Final Conclusion

All five `ApiKeyManager` unit tests passed individually and in the combined test run.

The tests verify:

- Environment variable API key loading.
- Missing API key validation.
- ECS JSON secret loading.
- Invalid ECS secret handling and environment fallback.
- Error handling for requests involving unavailable API keys.

**Scope limitation:** These results cover `ApiKeyManager` only. They do not yet verify `ModelLoader` initialization, embedding model selection, LLM provider selection, or model-construction failures. Those require additional tests, preferably using mocks to avoid real external API calls.