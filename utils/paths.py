"""Filesystem path helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).resolve().parents[1]


def resolve_project_path(relative_path: str) -> Path:
    """Resolve a project-relative path into an absolute path."""
    return project_root() / relative_path


def ensure_storage_directories(settings: dict[str, Any]) -> list[Path]:
    """Create configured local storage directories if they do not exist."""
    storage = settings["storage"]
    directory_keys = (
        "raw_data_dir",
        "processed_data_dir",
        "universe_data_dir",
        "signals_data_dir",
        "logs_dir",
    )

    created_or_existing: list[Path] = []
    for key in directory_keys:
        directory = resolve_project_path(storage[key])
        directory.mkdir(parents=True, exist_ok=True)
        created_or_existing.append(directory)

    return created_or_existing
