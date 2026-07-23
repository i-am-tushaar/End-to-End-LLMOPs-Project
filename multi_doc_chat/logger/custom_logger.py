import os
import logging
from datetime import datetime
import structlog


class CustomLogger:
    def __init__(self, log_dir="logs"):
        # Create a logs folder in the project if it doesn't exist
        self.logs_dir = os.path.join(os.getcwd(), log_dir)
        os.makedirs(self.logs_dir, exist_ok=True)

        # Create a unique log file using the current date and time
        log_file = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"
        self.log_file_path = os.path.join(self.logs_dir, log_file)

    def get_logger(self, name=__file__):
        # Use the current file name as the logger name
        logger_name = os.path.basename(name)

        # Save logs to a file
        file_handler = logging.FileHandler(self.log_file_path)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter("%(message)s"))

        # Show logs in the terminal
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter("%(message)s"))

        # Configure Python's logging system
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            handlers=[console_handler, file_handler]
        )

        # Configure structured JSON logging
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(
                    fmt="iso", utc=True, key="timestamp"
                ),  # Add timestamp
                structlog.processors.add_log_level,          # Add log level
                structlog.processors.EventRenamer(to="event"), # Rename message key
                structlog.processors.JSONRenderer()          # Output logs as JSON
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,  # Reuse the same logger
        )

        # Return the configured logger
        return structlog.get_logger(logger_name)