# read_dd.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def read_dd_file(tc: TimesModelClass, dd_path: Path) -> None:
    """Safely reads a .dd file."""

    # Check if file exists
    if not dd_path.exists():
        raise FileNotFoundError(f"CRITICAL: Data file not found: {dd_path.absolute()}")

    try:
        dd_content = dd_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        dd_content = dd_path.read_text(encoding="latin-1")

    tc.logger.info(f"Reading data from {dd_path.name}...")

    # Include .dd file
    tc.container.addGamsCode("$onmulti\n" + dd_content + "\n$offmulti")

    tc.logger.debug(f"Successfully loaded data from {dd_path.name}.")
