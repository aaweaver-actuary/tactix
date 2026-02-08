"""Time control parsing helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass

_TIME_CONTROL_LABELS = {"bullet", "blitz", "rapid", "classical", "unknown"}
_TIME_CONTROL_ALIASES = {
    "correspondence": "classical",
    "daily": "classical",
}
_TIME_CONTROL_ESTIMATE_MOVES = 40
_BULLET_MAX_SECONDS = 180
_BLITZ_MAX_SECONDS = 600
_RAPID_MAX_SECONDS = 1800


def _parse_time_control_value(value: str) -> ChessTimeControl | None:
    normalized = value.strip()
    if not normalized or normalized == "-":
        return None
    for parser in (
        _parse_time_control_plus,
        _parse_time_control_seconds,
        _parse_time_control_slash,
        _parse_time_control_fallback,
    ):
        parsed = parser(normalized)
        if parsed is not None:
            return parsed
    return None


def _parse_time_control_plus(value: str) -> ChessTimeControl | None:
    if "+" not in value:
        return None
    initial_str, increment_str = value.split("+", 1)
    if initial_str.isdigit() and increment_str.isdigit():
        return ChessTimeControl(initial=int(initial_str), increment=int(increment_str))
    return None


def _parse_time_control_seconds(value: str) -> ChessTimeControl | None:
    if value.isdigit():
        return ChessTimeControl(initial=int(value), increment=None)
    return None


def _parse_time_control_slash(value: str) -> ChessTimeControl | None:
    parts = _split_time_control_slash(value)
    return _parse_time_control_slash_parts(parts)


def _split_time_control_slash(value: str) -> list[str] | None:
    if "/" not in value:
        return None
    parts = [part for part in value.split("/") if part]
    return parts or None


def _parse_time_control_slash_parts(parts: list[str] | None) -> ChessTimeControl | None:
    if not parts:
        return None
    last = parts[-1]
    if not last.isdigit():
        return None
    return ChessTimeControl(initial=int(last), increment=None)


def _parse_time_control_fallback(value: str) -> ChessTimeControl | None:
    match = re.search(r"(\d+)", value)
    if match:
        return ChessTimeControl(initial=int(match.group(1)), increment=None)
    return None


def normalize_time_control_label(value: str | None) -> str:
    """Normalize a PGN time control string into a standard bucket."""
    normalized = _normalize_time_control_input(value)
    if not normalized:
        return "unknown"
    direct = _direct_time_control_label(normalized)
    if direct is not None:
        return direct
    parsed = _parse_time_control_value(normalized)
    if parsed is None:
        return "unknown"
    return _bucket_time_control_seconds(parsed.estimated_total_seconds())


def _normalize_time_control_input(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if not normalized or normalized == "-":
        return ""
    return normalized


def _direct_time_control_label(value: str) -> str | None:
    if value in _TIME_CONTROL_LABELS:
        return value
    return _TIME_CONTROL_ALIASES.get(value)


def _bucket_time_control_seconds(total_seconds: int) -> str:
    if total_seconds <= _BULLET_MAX_SECONDS:
        return "bullet"
    if total_seconds < _BLITZ_MAX_SECONDS:
        return "blitz"
    if total_seconds < _RAPID_MAX_SECONDS:
        return "rapid"
    return "classical"


@dataclass
class ChessTimeControl:
    """Represents a chess time control value."""

    initial: int  # initial time in seconds
    increment: int | None = None  # increment in seconds, if any

    @classmethod
    def from_pgn_string(cls, time_control_str: str) -> ChessTimeControl | None:
        """Parse a PGN time control string into a model."""
        if time_control_str == "-":
            return None
        if "+" in time_control_str:
            initial_str, increment_str = time_control_str.split("+", 1)
            return cls(initial=int(initial_str), increment=int(increment_str))
        return cls(initial=int(time_control_str), increment=None)

    def as_str(self) -> str:
        """Return the time control string representation."""
        if self.increment is not None:
            return f"{self.initial}+{self.increment}"
        return str(self.initial)

    def __str__(self) -> str:
        """Return the string representation of the time control."""
        return self.as_str()

    def estimated_total_seconds(self, moves: int = _TIME_CONTROL_ESTIMATE_MOVES) -> int:
        """Return an estimated total duration in seconds for bucketing."""
        increment = self.increment or 0
        return self.initial + increment * moves
