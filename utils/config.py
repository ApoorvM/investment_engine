"""Configuration loading utilities."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


def load_settings(config_path: Path | None = None) -> dict[str, Any]:
    """Load project settings from TOML."""
    path = config_path or Path("config/settings.toml")
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("rb") as file:
        return tomllib.load(file)
