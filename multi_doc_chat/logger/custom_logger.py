"""
custom_logger.py

Provides structured JSON logging for the application.
Logs are written to both the console and a timestamped log file.
"""

import logging
import os
from datetime import datetime
import structlog


class CustomLogger:
    """Configure and provide a structured JSON logger."""

    
    def __init__(self, log_dir: str = "logs"):
        """Create the project-level logs directory and timestamped log file."""

        from pathlib import Path

        # Project root: End-to-End-LLMOPs-Project
        project_root = Path(r"F:\AI Projects\End-to-End-LLMOPs-Project")

        # Always store logs in the project root/logs directory
        logs_dir = project_root / log_dir
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Create a timestamped log file
        log_file = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"
        self.log_file_path = str(logs_dir / log_file)

        self._configure()

    def _configure(self) -> None:
        """Configure console/file handlers and JSON log formatting."""

        # structlog creates the JSON message; logging writes it to outputs.
        formatter = logging.Formatter("%(message)s")

        file_handler = logging.FileHandler(self.log_file_path)
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logging.basicConfig(
            level=logging.INFO,
            handlers=[console_handler, file_handler],
        )

        # Add common fields and render every log as JSON.
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(
                    fmt="iso", utc=True, key="timestamp"
                ),
                structlog.processors.add_log_level,
                structlog.processors.EventRenamer(to="event"),
                structlog.processors.JSONRenderer(),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    def get_logger(self, name: str | None = None):
        """Return a structured logger for the given module/file."""
        logger_name = os.path.basename(name or __file__)
        return structlog.get_logger(logger_name)


# Global logger instance used across the project
GLOBAL_LOGGER = CustomLogger().get_logger(__name__)

if __name__ == "__main__":
    # Quick manual test.
    logger = CustomLogger().get_logger(__file__)
    logger.info(
        "data_ingestion_started",
        file_name="essay.txt",
        chunk_size=200,
    )


# =============================================================================
# CUSTOM LOGGER - PURPOSE & FLOW
# =============================================================================
#
# Purpose:
# Provides structured JSON logs for debugging, monitoring, and error tracking.
#
#   Application Module
#         │
#         ▼
#   logger.info/error/warning()
#         │
#         ▼
#      structlog
#         │
#   Add timestamp, level, event
#         │
#         ▼
#      JSON Log
#         │
#      ┌──┴───┐
#      ▼      ▼
#   Console  logs/*.log
#
# Example:
# logger.info("documents_loaded", count=10)
#
# Output:
# {"count": 10, "timestamp": "...", "level": "info",
#  "event": "documents_loaded"}
#
# =============================================================================