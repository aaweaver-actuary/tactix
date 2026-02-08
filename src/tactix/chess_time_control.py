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
    parsed = None
    if "+" in normalized:
        initial_str, increment_str = normalized.split("+", 1)
        if initial_str.isdigit() and increment_str.isdigit():
            parsed = ChessTimeControl(initial=int(initial_str), increment=int(increment_str))
    if parsed is None and normalized.isdigit():
        parsed = ChessTimeControl(initial=int(normalized), increment=None)
    if parsed is None and "/" in normalized:
        parts = [part for part in normalized.split("/") if part]
        if parts and parts[-1].isdigit():
            parsed = ChessTimeControl(initial=int(parts[-1]), increment=None)
    if parsed is None:
        match = re.search(r"(\d+)", normalized)
        if match:
            parsed = ChessTimeControl(initial=int(match.group(1)), increment=None)
    return parsed


def normalize_time_control_label(value: str | None) -> str:
    """Normalize a PGN time control string into a standard bucket."""
    label = "unknown"
    normalized = (value or "").strip().lower()
    if normalized and normalized != "-":
        if normalized in _TIME_CONTROL_LABELS:
            label = normalized
        elif normalized in _TIME_CONTROL_ALIASES:
            label = _TIME_CONTROL_ALIASES[normalized]
        else:
            parsed = _parse_time_control_value(normalized)
            if parsed is not None:
                total_seconds = parsed.estimated_total_seconds()
                if total_seconds <= _BULLET_MAX_SECONDS:
                    label = "bullet"
                elif total_seconds < _BLITZ_MAX_SECONDS:
                    label = "blitz"
                elif total_seconds < _RAPID_MAX_SECONDS:
                    label = "rapid"
                else:
                    label = "classical"
    return label


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
