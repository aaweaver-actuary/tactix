"""Dataclass inputs for PGN upsert operations."""

# pylint: disable=invalid-name

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PgnUpsertInputs:  # pylint: disable=too-many-instance-attributes
    """Inputs needed to build a PGN upsert plan."""

    pgn_text: str
    user: str
    latest_hash: str | None
    latest_version: int
    normalize_pgn: Callable[[str], str] | None = None
    hash_pgn: Callable[[str], str] | None = None
    fetched_at: datetime | None = None
    ingested_at: datetime | None = None
    last_timestamp_ms: int = 0
    cursor: object | None = None
