from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChessTimeControl:
    initial: int  # initial time in seconds
    increment: int | None = None  # increment in seconds, if any

    @classmethod
    def from_pgn_string(cls, time_control_str: str) -> ChessTimeControl | None:
        if time_control_str == "-":
            return None
        if "+" in time_control_str:
            initial_str, increment_str = time_control_str.split("+", 1)
            return cls(initial=int(initial_str), increment=int(increment_str))
        return cls(initial=int(time_control_str), increment=None)

    def as_str(self) -> str:
        if self.increment is not None:
            return f"{self.initial}+{self.increment}"
        return str(self.initial)

    def __str__(self) -> str:
        return self.as_str()
