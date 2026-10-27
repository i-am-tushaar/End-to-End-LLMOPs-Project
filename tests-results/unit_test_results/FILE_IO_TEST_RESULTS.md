# File I/O Unit Test Results

## 1. Overview

- **Module tested:** `multi_doc_chat/utils/file_io.py`
- **Test file:** `tests/unit/test_file_io.py`
- **Testing framework:** pytest
- **Test type:** Unit testing

## 2. Test Execution

Command:

```bash
uv run pytest tests/unit/test_file_io.py -v
```

Result:

| Metric          | Result       |
| --------------- | -----------: |
| Total tests     |           24 |
| Passed          |           24 |
| Failed          |            0 |
| Execution time  | 0.80 seconds |
| Status          |   **PASSED** |

The 24 results come from 14 test functions. Thirteen run once each, and `test_supported_extensions_are_saved` is parametrized, so it runs once for each of the 11 supported file extensions (13 + 11 = 24).

## 3. Test Coverage by Function

| Function tested         | Test functions | Results | What was verified                                                                                   |
| ----------------------- | -------------: | ------: | --------------------------------------------------------------------------------------------------- |
| `_get_filename()`       |              3 |       3 | Priority of `filename` over `name`, fallback to `name`, and the default name `file`                 |
| `_read_bytes()`         |              4 |       4 | Reading from an upload object's `file` attribute, from `read()`, from `getbuffer()` (memoryview converted to bytes), and `ValueError` for unsupported objects |
| `_safe_filename()`      |              2 |       2 | Removal of unsafe characters with the extension preserved, and unique names for repeated filenames  |
| `save_uploaded_files()` |              5 |      15 | Saving all 11 supported extensions, skipping unsupported extensions, creating the target directory, handling an empty list, and wrapping read errors |
| **Total**               |         **14** |  **24** |                                                                                                     |

## 4. Detailed Test Results

### 4.1 `_get_filename()`

- `test_get_filename_from_upload_file`: verifies that `filename` takes priority over `name`.
- `test_get_filename_from_generic_file`: verifies that `name` is used when `filename` is unavailable.
- `test_get_filename_uses_default_name`: verifies that `file` is returned when neither attribute exists.

### 4.2 `_read_bytes()`

- `test_read_bytes_from_upload_file`: verifies reading from an upload object's `file` attribute.
- `test_read_bytes_from_regular_file_object`: verifies reading directly with `read()`.
- `test_read_bytes_from_getbuffer_object`: verifies that memoryview content is converted into `bytes`.
- `test_read_bytes_rejects_unsupported_object`: verifies that an object without a supported reading method raises `ValueError`.

### 4.3 `_safe_filename()`

- `test_safe_filename_removes_unsafe_characters`: verifies that unsafe characters are replaced, the extension is kept, and the name starts with `my_report_`.
- `test_safe_filename_generates_unique_names`: verifies that repeated calls with the same filename return different names.

### 4.4 `save_uploaded_files()`

- `test_supported_extensions_are_saved`: parametrized, runs 11 times (once per supported extension) and verifies the saved path, suffix, and content.
- `test_unsupported_extension_is_skipped`: verifies that an unsupported file such as `malware.exe` is skipped and nothing is written.
- `test_save_uploaded_files_creates_target_directory`: verifies that a missing destination directory is created.
- `test_save_uploaded_files_with_empty_list`: verifies that an empty upload list returns an empty list.
- `test_save_uploaded_files_wraps_read_errors`: verifies that an `OSError` raised while reading is wrapped in `DocumentPortalException`.

## 5. Functional Coverage

- Filename retrieval, including the priority order and the default filename.
- Reading uploaded files through supported interfaces: `file` attribute, `read()`, and `getbuffer()`.
- Rejecting unsupported file objects.
- Removing unsafe filename characters and generating unique names.
- Saving all 11 supported file extensions.
- Skipping unsupported file extensions.
- Creating destination directories automatically.
- Handling empty upload lists.
- Wrapping file reading errors in `DocumentPortalException`.

## 6. Conclusion

All 24 unit tests passed. The tested file I/O utilities behaved as expected for the scenarios covered by this test suite.

**Limitation:** These tests use in memory objects and temporary directories. They do not prove that real uploads through the API endpoints work in production, so those should also be checked with integration tests.