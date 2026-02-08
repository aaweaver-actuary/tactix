"""Normalize player names from PGN headers."""

from __future__ import annotations

import re

_ANNOTATION_SPLIT = re.compile(r"\s*[\(\[\{]", re.UNICODE)


def _normalize_player_name(value: object | None) -> str:
    """Return a normalized player identifier for comparisons."""
    if value is None:
        return ""
    text = str(value).strip().lower()
    if not text:
        return ""
    return _ANNOTATION_SPLIT.split(text, maxsplit=1)[0].strip()


__all__ = ["_normalize_player_name"]
