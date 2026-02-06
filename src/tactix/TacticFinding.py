"""Domain finding for a detected tactic."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TacticFinding:
    """A detected tactical motif."""

    motif: str
