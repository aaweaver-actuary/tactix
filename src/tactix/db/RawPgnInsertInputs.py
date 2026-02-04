"""Inputs used to insert raw PGN rows."""

# pylint: disable=invalid-name

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from tactix.define_pgn_upsert_plan__db_store import PgnUpsertPlan


@dataclass(frozen=True)
class RawPgnInsertInputs:
    """Grouped inputs for raw PGN inserts."""

    raw_pgn_id: int
    game_id: str
    source: str
    row: Mapping[str, object]
    plan: PgnUpsertPlan
