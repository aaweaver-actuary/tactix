from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PgnUpsertHashing:
    normalize_pgn: Callable[[str], str] | None
    hash_pgn: Callable[[str], str] | None


@dataclass(frozen=True)
class PgnUpsertTimestamps:
    fetched_at: datetime | None
    ingested_at: datetime | None
    last_timestamp_ms: int


@dataclass(frozen=True)
class PgnUpsertInputs:
    pgn_text: str
    user: str
    latest_hash: str | None
    latest_version: int
    hashing: PgnUpsertHashing
    timestamps: PgnUpsertTimestamps
    cursor: object

    @property
    def normalize_pgn(self) -> Callable[[str], str] | None:
        return self.hashing.normalize_pgn

    @property
    def hash_pgn(self) -> Callable[[str], str] | None:
        return self.hashing.hash_pgn

    @property
    def fetched_at(self) -> datetime | None:
        return self.timestamps.fetched_at

    @property
    def ingested_at(self) -> datetime | None:
        return self.timestamps.ingested_at

    @property
    def last_timestamp_ms(self) -> int:
        return self.timestamps.last_timestamp_ms
