"""Protocol for tactic detector strategy objects."""

# pylint: disable=too-few-public-methods

from __future__ import annotations

from typing import Protocol, runtime_checkable

from tactix.TacticContext import TacticContext
from tactix.TacticFinding import TacticFinding


@runtime_checkable
class TacticDetector(Protocol):
    """Interface for tactic detector strategies."""

    motif: str

    def detect(self, context: TacticContext) -> list[TacticFinding]:
        """Return domain findings for a tactic context."""
