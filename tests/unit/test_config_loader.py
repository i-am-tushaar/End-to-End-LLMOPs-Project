
# Import pytest utilities are not needed for this test.
from multi_doc_chat.utils.config_loader import load_config
import pytest


def test_load_config_success(tmp_path):
    """
    Test that load_config() reads a valid YAML file
    and returns its contents as a Python dictionary.
    """

    # Step 1: Create a temporary YAML configuration file.
    config_file = tmp_path / "config.yaml"

    # Step 2: Write valid YAML content into the file.
    config_file.write_text(
        "llm:\n  provider: google\n",
        encoding="utf-8",
    )

    # Step 3: Call the function being tested.
    result = load_config(str(config_file))

    # Step 4: Verify the returned dictionary matches expectations.
    assert result == {"llm": {"provider": "google"}}


def test_load_config_missing_file(tmp_path):
    """
    Test that load_config() raises FileNotFoundError
    when the configuration file does not exist.
    """

    # Step 1: Define a path to a nonexistent file.
    config_file = tmp_path / "missing.yaml"

    # Step 2: Verify that the expected exception is raised.
    with pytest.raises(
        FileNotFoundError,
        match="Config file not found",
    ):
        load_config(str(config_file))


def test_load_config_empty_file(tmp_path):
    """
    Test that an empty YAML file returns an empty dictionary.
    """

    # Step 1: Create a temporary YAML file.
    config_file = tmp_path / "empty.yaml"

    # Step 2: Write empty content to the file.
    config_file.write_text("", encoding="utf-8")

    # Step 3: Load the empty configuration file.
    result = load_config(str(config_file))

    # Step 4: Verify that the result is an empty dictionary.
    assert result == {}


import yaml


def test_load_config_invalid_yaml(tmp_path):
    """
    Test that invalid YAML syntax raises yaml.YAMLError.
    """

    # Step 1: Create a temporary YAML file.
    config_file = tmp_path / "invalid.yaml"

    # Step 2: Write deliberately invalid YAML syntax.
    config_file.write_text(
        "key: [unclosed",
        encoding="utf-8",
    )

    # Step 3: Verify that loading the file raises a YAML error.
    with pytest.raises(yaml.YAMLError):
        load_config(str(config_file))



def test_load_config_relative_path(tmp_path, monkeypatch):
    """
    Test that a relative configuration path is resolved
    from the project root.
    """

    # Step 1: Import the config_loader module.
    import multi_doc_chat.utils.config_loader as config_module

    # Step 2: Create a temporary configuration file.
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "app_name: test_app",
        encoding="utf-8",
    )

    # Step 3: Temporarily treat tmp_path as the project root.
    monkeypatch.setattr(
        config_module,
        "_project_root",
        lambda: tmp_path,
    )

    # Step 4: Load the file using only its relative path.
    result = load_config("config.yaml")

    # Step 5: Verify the loaded configuration.
    assert result == {"app_name": "test_app"}
