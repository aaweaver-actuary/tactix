"""Time control parsing helpers."""

from __future__ import annotations

from dataclasses import dataclass


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
