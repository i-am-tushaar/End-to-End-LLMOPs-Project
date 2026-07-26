"""
config_loader.py

Loads the project's YAML configuration file.
Supports explicit paths, environment variables, and a default config location.
"""

import os
from pathlib import Path

import yaml


def _project_root() -> Path:
    """Return the project root directory."""
    # utils/config_loader.py -> project root
    return Path(__file__).resolve().parents[1]


def _resolve_path(config_path: str | None) -> Path:
    """
    Resolve the config file path.

    Priority:
        1. Path passed to load_config()
        2. CONFIG_PATH environment variable
        3. Default: <project_root>/config/config.yaml
    """
    path = Path(
        config_path
        or os.getenv("CONFIG_PATH")
        or _project_root() / "config" / "config.yaml"
    )

    # Resolve relative paths from the project root.
    if not path.is_absolute():
        path = _project_root() / path

    return path


def load_config(config_path: str | None = None) -> dict:
    """Load config.yaml and return its contents as a dictionary."""
    path = _resolve_path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


if __name__ == "__main__":
    # Quick manual test.
    print(load_config())


# =============================================================================
# CONFIG LOADER - PURPOSE & FLOW
# =============================================================================
#
# Purpose:
# Finds and loads config.yaml so other modules can access project settings.
#
#   load_config()
#        │
#        ▼
#   _resolve_path()
#        │
#        ├── 1. Provided config_path
#        ├── 2. CONFIG_PATH from environment
#        └── 3. Default config/config.yaml
#        │
#        ▼
#   Check file exists
#        │
#        ▼
#   yaml.safe_load()
#        │
#        ▼
#   Python Dictionary
#        │
#        ▼
#   ModelLoader / Data Ingestion / Other Modules
#
# =============================================================================