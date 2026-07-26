from pathlib import Path
import os
import yaml


def _project_root() -> Path:
    """Return the project's top level folder, two levels up from this file."""
    return Path(__file__).resolve().parents[1]


def _resolve_path(config_path: str | None) -> Path:
    """
    Work out which config file to use, in priority order:
      1. an explicit path passed into load_config()
      2. the CONFIG_PATH environment variable
      3. a default path: <project_root>/config/config.yaml
    Relative paths are made absolute by anchoring them to the project root.
    """
    path = Path(config_path or os.getenv("CONFIG_PATH") or _project_root() / "config" / "config.yaml")

    if not path.is_absolute():
        path = _project_root() / path

    return path


def load_config(config_path: str | None = None) -> dict:
    """Load and parse the YAML config file, resolved via _resolve_path()."""
    path = _resolve_path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


if __name__ == "__main__":
    # Quick manual check: print the resolved config to confirm it loads correctly
    print(load_config())
