"""
custom_exception.py

Provides a custom exception with useful debugging information such as
the error message, source file, line number, and traceback.
"""

import sys
import traceback
from typing import Optional


class DocumentPortalException(Exception):
    """Custom exception that adds file, line, and traceback details."""

    def __init__(self, error_message, error_details: Optional[object] = None):
        self.error_message = str(error_message)

        # Get information about the original exception.
        exc_type, exc_value, exc_tb = self._get_exc_info(error_details)

        # Move to the last traceback frame where the actual error occurred.
        while exc_tb and exc_tb.tb_next:
            exc_tb = exc_tb.tb_next

        self.file_name = exc_tb.tb_frame.f_code.co_filename if exc_tb else "<unknown>"
        self.lineno = exc_tb.tb_lineno if exc_tb else -1

        # Store full traceback for debugging/logging.
        self.traceback_str = (
            "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
            if exc_tb else ""
        )

        super().__init__(str(self))

    @staticmethod
    def _get_exc_info(error_details):
        """
        Return exception type, value, and traceback.

        Supports:
        - Exception object: DocumentPortalException("message", e)
        - sys module:        DocumentPortalException("message", sys)
        - None:              Uses the currently handled exception
        """
        if isinstance(error_details, BaseException):
            return type(error_details), error_details, error_details.__traceback__

        if hasattr(error_details, "exc_info"):
            return error_details.exc_info()

        return sys.exc_info()

    def __str__(self):
        """Return a human-readable error message."""
        message = (
            f"Error in [{self.file_name}] at line [{self.lineno}] "
            f"| Message: {self.error_message}"
        )

        return (
            f"{message}\nTraceback:\n{self.traceback_str}"
            if self.traceback_str else message
        )

    def __repr__(self):
        """Return a developer-friendly representation for debugging."""
        return (
            f"DocumentPortalException(file={self.file_name!r}, "
            f"line={self.lineno}, message={self.error_message!r})"
        )


if __name__ == "__main__":
    # Quick manual test: wrap a normal Python error.
    try:
        1 / 0
    except Exception as e:
        raise DocumentPortalException("Division failed", e) from e


# =============================================================================
# CUSTOM EXCEPTION - PURPOSE & FLOW
# =============================================================================
#
# Purpose:
# Adds useful debugging details to application errors.
#
#   Python/Application Error
#            │
#            ▼
#   DocumentPortalException
#            │
#            ├── Error message
#            ├── File name
#            ├── Line number
#            └── Traceback
#            │
#            ▼
#      Logger / Console
#
# Example:
#
#   try:
#       load_documents(...)
#   except Exception as e:
#       raise DocumentPortalException("Failed to load documents", e) from e
#
# =============================================================================