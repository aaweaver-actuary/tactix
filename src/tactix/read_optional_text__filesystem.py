"""Read optional filesystem text content."""

from __future__ import annotations

from pathlib import Path


def _read_optional_text(path: Path) -> str | None:
    try:
        raw = path.read_text().strip()
    except FileNotFoundError:
        return None
    return raw or None
