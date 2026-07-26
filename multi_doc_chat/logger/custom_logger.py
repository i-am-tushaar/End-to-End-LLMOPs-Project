import os
import logging
from datetime import datetime
import structlog


class CustomLogger:
    """Structured JSON logger that writes to both the console and a timestamped log file."""

    def __init__(self, log_dir="logs"):
        # Create a logs folder in the project if it doesn't exist
        logs_dir = os.path.join(os.getcwd(), log_dir)
        os.makedirs(logs_dir, exist_ok=True)

        # Create a unique log file using the current date and time
        log_file = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"
        self.log_file_path = os.path.join(logs_dir, log_file)

        self._configure()

    def _configure(self):
        """Set up console and file output, then structured JSON formatting. Runs once."""
        formatter = logging.Formatter("%(message)s")

        file_handler = logging.FileHandler(self.log_file_path)
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logging.basicConfig(level=logging.INFO, handlers=[console_handler, file_handler])

        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),  # Add timestamp
                structlog.processors.add_log_level,             # Add log level
                structlog.processors.EventRenamer(to="event"),  # Rename message key
                structlog.processors.JSONRenderer(),             # Output logs as JSON
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    def get_logger(self, name=None):
        """Return a logger named after the calling file, e.g. get_logger(__name__)."""
        logger_name = os.path.basename(name or __file__)
        return structlog.get_logger(logger_name)


if __name__ == "__main__":
    logger = CustomLogger().get_logger(__file__)
    logger.info("data_ingestion_started", file_name="essay.txt", chunk_size=200)
