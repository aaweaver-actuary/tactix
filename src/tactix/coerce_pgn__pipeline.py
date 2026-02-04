"""Coerce PGN payloads to text."""

from __future__ import annotations

from tactix.coerce_str__pipeline import _coerce_str


def _coerce_pgn(value: object) -> str:
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    return _coerce_str(value)
