import sys

from multi_doc_chat.exception.custom_exception import DocumentPortalException


# ## Test 1: Store the error message
# Objective: Verify that the custom exception stores the supplied
# error message and includes it in its string representation.
def test_custom_exception_stores_error_message():

    error = DocumentPortalException("Failed to load documents")

    assert error.error_message == "Failed to load documents"
    assert "Failed to load documents" in str(error)


# ## Test 2: Capture filename and line number
# Objective: Verify that the custom exception captures the source
# filename and line number from the original exception traceback.
def test_custom_exception_captures_file_and_line():

    try:
        raise ValueError("Original error")
    except ValueError as original_error:
        error = DocumentPortalException(
            "Document processing failed",
            original_error,
        )

    assert error.file_name != "<unknown>"
    assert error.lineno > 0
    assert error.file_name.endswith("test_custom_exception.py")


# ## Test 3: Include the original traceback
# Objective: Verify that the original exception traceback is stored
# and included in the custom exception's string representation.
def test_custom_exception_includes_traceback_for_original_exception():

    try:
        raise ValueError("Original error")
    except ValueError as original_error:
        error = DocumentPortalException(
            "Document processing failed",
            original_error,
        )

    assert "ValueError: Original error" in error.traceback_str
    assert "Traceback:" in str(error)


# ## Test 4: Generate the developer-friendly representation
# Objective: Verify that repr() includes the exception class,
# filename, line number, and error message.
def test_custom_exception_repr():

    error = DocumentPortalException("Document loading failed")

    result = repr(error)

    assert "DocumentPortalException" in result
    assert "file=" in result
    assert "line=" in result
    assert "Document loading failed" in result


# ## Test 5: Handle a missing traceback
# Objective: Verify that when no exception is currently active,
# the custom exception uses an unknown filename, line number -1,
# and an empty traceback.
def test_custom_exception_without_traceback_uses_unknown_location():

    error = DocumentPortalException("No active exception")

    assert error.file_name == "<unknown>"
    assert error.lineno == -1
    assert error.traceback_str == ""
    assert "No active exception" in str(error)


# ## Test 6: Capture the currently handled exception
# Objective: Verify that the current exception is automatically
# captured when no error_details argument is provided.
def test_custom_exception_uses_current_exception():

    try:
        raise ValueError("Current error")
    except ValueError:
        error = DocumentPortalException("Wrapped current error")

    assert "ValueError: Current error" in error.traceback_str
    assert error.file_name.endswith("test_custom_exception.py")
    assert error.lineno > 0


# ## Test 7: Capture exception details using the sys module
# Objective: Verify that the custom exception obtains the active
# exception's type, value, and traceback through sys.exc_info().
def test_custom_exception_accepts_sys_module():

    try:
        raise ValueError("System exception")
    except ValueError:
        error = DocumentPortalException(
            "Wrapped system exception",
            sys,
        )

    assert "ValueError: System exception" in error.traceback_str
    assert error.file_name.endswith("test_custom_exception.py")
    assert error.lineno > 0
