"""Logging setup for local runs."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from utils.paths import resolve_project_path


def setup_logging(settings: dict[str, Any]) -> logging.Logger:
    """Configure console and file logging for the application."""
    log_level_name = settings["logging"].get("level", "INFO")
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    log_dir = resolve_project_path(settings["storage"]["logs_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file: Path = log_dir / settings["logging"]["file_name"]

    logger = logging.getLogger("investment_engine")
    logger.setLevel(log_level)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger
