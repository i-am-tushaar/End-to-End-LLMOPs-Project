import sys
import traceback
from typing import Optional


class DocumentPortalException(Exception):
    """Exception that also records which file and line the underlying error came from."""

    def __init__(self, error_message, error_details: Optional[object] = None):
        self.error_message = str(error_message)

        exc_type, exc_value, exc_tb = self._get_exc_info(error_details)

        # Walk to the last frame in the traceback, since that is where the
        # error actually occurred (earlier frames are just the call chain)
        while exc_tb and exc_tb.tb_next:
            exc_tb = exc_tb.tb_next

        self.file_name = exc_tb.tb_frame.f_code.co_filename if exc_tb else "<unknown>"
        self.lineno = exc_tb.tb_lineno if exc_tb else -1

        # Save the full traceback as text, for logging or debugging later
        self.traceback_str = (
            "".join(traceback.format_exception(exc_type, exc_value, exc_tb)) if exc_tb else ""
        )

        super().__init__(str(self))

    @staticmethod
    def _get_exc_info(error_details):
        """
        Work out (exc_type, exc_value, exc_tb) no matter what was passed in:
          - an exception instance, e.g. DocumentPortalException("msg", e)
          - the sys module, e.g. DocumentPortalException("msg", sys)
          - nothing, in which case grab whatever exception is currently being handled
        """
        if isinstance(error_details, BaseException):
            return type(error_details), error_details, error_details.__traceback__
        if hasattr(error_details, "exc_info"):  # the sys module
            return error_details.exc_info()
        return sys.exc_info()

    def __str__(self):
        # Human readable message shown when the exception is printed or logged
        base = f"Error in [{self.file_name}] at line [{self.lineno}] | Message: {self.error_message}"
        return f"{base}\nTraceback:\n{self.traceback_str}" if self.traceback_str else base

    def __repr__(self):
        # Developer friendly representation, useful in a debugger or REPL
        return (
            f"DocumentPortalException(file={self.file_name!r}, "
            f"line={self.lineno}, message={self.error_message!r})"
        )


if __name__ == "__main__":
    # Quick manual check: raise a normal error, then wrap and re-raise it
    try:
        1 / 0
    except Exception as e:
        raise DocumentPortalException("Division failed", e) from e
