from pathlib import Path
import os
import yaml


def _project_root() -> Path:
    # Get the project root folder
    return Path(__file__).resolve().parents[1]


def load_config(config_path: str | None = None) -> dict:
    # Use: function argument > environment variable > default config path
    env_path = os.getenv("CONFIG_PATH")
    if config_path is None:
        config_path = env_path or str(_project_root() / "config" / "config.yaml")

    path = Path(config_path)

    # Convert relative path to absolute path
    if not path.is_absolute():
        path = _project_root() / path

    # Check if the config file exists
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    # Read and return the YAML configuration
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}