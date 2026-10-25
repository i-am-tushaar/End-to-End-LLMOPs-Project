from pathlib import Path

import pytest

import multi_doc_chat.logger.custom_logger as logger_module
from multi_doc_chat.logger.custom_logger import CustomLogger


# Test 1: Initialize the custom logger
# Objective: Verify that CustomLogger creates the logs directory
# and a timestamped log file during initialization.
def test_custom_logger_initialization(tmp_path, monkeypatch):
    # Replace the hardcoded project root with a temporary directory.
    project_root = tmp_path

    class FakePath(Path):
        pass

    monkeypatch.setattr(
        logger_module,
        "CustomLogger",
        CustomLogger,
    )

    # Create the logger using a temporary logs directory.
    logger = CustomLogger(log_dir=str(project_root / "logs"))

    assert logger.log_file_path.endswith(".log")
    assert Path(logger.log_file_path).parent.exists()



import logging
from unittest.mock import MagicMock

import structlog

from multi_doc_chat.logger.custom_logger import CustomLogger


# Test 2: Configure logging handlers
# Objective: Verify that _configure() sets the INFO level
# and configures console and file handlers.
def test_configure_sets_handlers_and_info_level(monkeypatch, tmp_path):
    logger = CustomLogger.__new__(CustomLogger)
    logger.log_file_path = str(tmp_path / "test.log")

    basic_config_mock = MagicMock()
    structlog_configure_mock = MagicMock()

    monkeypatch.setattr(logging, "basicConfig", basic_config_mock)
    monkeypatch.setattr(structlog, "configure", structlog_configure_mock)

    logger._configure()

    basic_config_mock.assert_called_once()
    config_kwargs = basic_config_mock.call_args.kwargs

    assert config_kwargs["level"] == logging.INFO
    assert len(config_kwargs["handlers"]) == 2
    assert any(
        isinstance(handler, logging.FileHandler)
        for handler in config_kwargs["handlers"]
    )
    assert any(
        isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, logging.FileHandler)
        for handler in config_kwargs["handlers"]
    )

    structlog_configure_mock.assert_called_once()



from unittest.mock import MagicMock

import multi_doc_chat.logger.custom_logger as logger_module
from multi_doc_chat.logger.custom_logger import CustomLogger


# Test 3: Return a structured logger
# Objective: Verify that get_logger() returns the logger
# provided by structlog for the requested module name.
def test_get_logger_returns_structured_logger(monkeypatch):
    logger = CustomLogger.__new__(CustomLogger)
    get_logger_mock = MagicMock(return_value="mock_logger")

    monkeypatch.setattr(
        logger_module.structlog,
        "get_logger",
        get_logger_mock,
    )

    result = logger.get_logger("my_module.py")

    assert result == "mock_logger"
    get_logger_mock.assert_called_once_with("my_module.py")



# Test 4: Use the default logger name
# Objective: Verify that get_logger() uses the current module's
# filename when the caller does not provide a name.
def test_get_logger_uses_default_name(monkeypatch):
    logger = CustomLogger.__new__(CustomLogger)
    get_logger_mock = MagicMock(return_value="mock_logger")

    monkeypatch.setattr(
        logger_module.structlog,
        "get_logger",
        get_logger_mock,
    )
    monkeypatch.setattr(
        logger_module,
        "__file__",
        "/app/custom_logger.py",
    )

    result = logger.get_logger()

    assert result == "mock_logger"
    get_logger_mock.assert_called_once_with("custom_logger.py")



# Test 5: Configure JSON log rendering
# Objective: Verify that _configure() includes JSONRenderer
# in the structlog processor configuration.
def test_configure_includes_json_renderer(monkeypatch, tmp_path):
    logger = CustomLogger.__new__(CustomLogger)
    logger.log_file_path = str(tmp_path / "test.log")

    monkeypatch.setattr(logging, "basicConfig", MagicMock())

    captured_config = {}

    def fake_configure(**kwargs):
        captured_config.update(kwargs)

    monkeypatch.setattr(structlog, "configure", fake_configure)

    logger._configure()

    processors = captured_config["processors"]

    assert any(
        isinstance(processor, structlog.processors.JSONRenderer)
        for processor in processors
    )



# Test 6: Configure event renaming
# Objective: Verify that _configure() includes EventRenamer
# configured to rename the event field to "event".
def test_configure_includes_event_renamer(monkeypatch, tmp_path):
    logger = CustomLogger.__new__(CustomLogger)
    logger.log_file_path = str(tmp_path / "test.log")

    monkeypatch.setattr(logging, "basicConfig", MagicMock())

    captured_config = {}

    def fake_configure(**kwargs):
        captured_config.update(kwargs)

    monkeypatch.setattr(structlog, "configure", fake_configure)

    logger._configure()

    processors = captured_config["processors"]

    assert any(
        isinstance(processor, structlog.processors.EventRenamer)
        for processor in processors
    )



# Test 7: Configure timestamp generation
# Objective: Verify that _configure() includes TimeStamper
# with ISO formatting, UTC timestamps, and the "timestamp" key.
def test_configure_includes_timestamp_processor(monkeypatch, tmp_path):
    logger = CustomLogger.__new__(CustomLogger)
    logger.log_file_path = str(tmp_path / "test.log")

    monkeypatch.setattr(logging, "basicConfig", MagicMock())

    captured_config = {}

    def fake_configure(**kwargs):
        captured_config.update(kwargs)

    monkeypatch.setattr(structlog, "configure", fake_configure)

    logger._configure()

    processors = captured_config["processors"]

    assert any(
        isinstance(processor, structlog.processors.TimeStamper)
        for processor in processors
    )



# Test 8: Configure log level processing
# Objective: Verify that _configure() includes the processor
# that adds the log level to structured log entries.
def test_configure_includes_log_level_processor(monkeypatch, tmp_path):
    logger = CustomLogger.__new__(CustomLogger)
    logger.log_file_path = str(tmp_path / "test.log")

    monkeypatch.setattr(logging, "basicConfig", MagicMock())

    captured_config = {}

    def fake_configure(**kwargs):
        captured_config.update(kwargs)

    monkeypatch.setattr(structlog, "configure", fake_configure)

    logger._configure()

    processors = captured_config["processors"]

    assert structlog.processors.add_log_level in processors



# Test 9: Extract the filename from a full path
# Objective: Verify that get_logger() passes only the basename
# of the supplied path to structlog.get_logger().
def test_get_logger_extracts_basename(monkeypatch):
    logger = CustomLogger.__new__(CustomLogger)
    get_logger_mock = MagicMock(return_value="mock_logger")

    monkeypatch.setattr(
        logger_module.structlog,
        "get_logger",
        get_logger_mock,
    )

    result = logger.get_logger(r"F:\app\modules\data_ingestion.py")

    assert result == "mock_logger"
    get_logger_mock.assert_called_once_with("data_ingestion.py")