"""Build PGN upsert plans from raw rows."""

import importlib
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import cast

from tactix._hash_pgn_text import _hash_pgn_text
from tactix.base_db_store import BaseDbStore
from tactix.PgnUpsertInputs import PgnUpsertHashing, PgnUpsertInputs, PgnUpsertTimestamps
from tactix.PgnUpsertPlan import PgnUpsertPlan


def _resolve_postgres_store() -> object | None:
    try:
        return importlib.import_module("tactix.postgres_store")
    except ImportError:  # pragma: no cover - optional dependency in some environments
        return None


def _resolve_hash_pgn__pgn_upsert_plan(
    postgres_store: object | None,
) -> Callable[[str], str]:
    if postgres_store is None:
        return _hash_pgn_text
    return getattr(postgres_store, "_hash_pgn_text", _hash_pgn_text)


def _build_pgn_upsert_hashing__pgn_upsert_plan(
    hash_pgn: Callable[[str], str],
) -> PgnUpsertHashing:
    return PgnUpsertHashing(normalize_pgn=None, hash_pgn=hash_pgn)


def _build_pgn_upsert_timestamps__pgn_upsert_plan(
    row: Mapping[str, object],
) -> PgnUpsertTimestamps:
    # Justification: mapping raw row timestamps into a dedicated DTO needs multiple fields.
    return PgnUpsertTimestamps(
        fetched_at=cast(datetime | None, row.get("fetched_at")),
        ingested_at=cast(datetime | None, row.get("ingested_at")),
        last_timestamp_ms=cast(int, row.get("last_timestamp_ms", 0)),
    )


def _build_pgn_upsert_inputs__pgn_upsert_plan(
    row: Mapping[str, object],
    latest_hash: str | None,
    latest_version: int,
    hash_pgn: Callable[[str], str],
) -> PgnUpsertInputs:
    # Justification: assembling the input DTO requires multiple fields from the raw row.
    return PgnUpsertInputs(
        pgn_text=str(row.get("pgn") or ""),
        user=str(row.get("user") or ""),
        latest_hash=latest_hash,
        latest_version=latest_version,
        hashing=_build_pgn_upsert_hashing__pgn_upsert_plan(hash_pgn),
        timestamps=_build_pgn_upsert_timestamps__pgn_upsert_plan(row),
        cursor=row.get("cursor"),
    )


def _build_pgn_upsert_plan(
    row: Mapping[str, object],
    latest_hash: str | None,
    latest_version: int,
) -> PgnUpsertPlan | None:
    """Return a PGN upsert plan for the given raw row."""
    hash_pgn = _resolve_hash_pgn__pgn_upsert_plan(_resolve_postgres_store())
    inputs = _build_pgn_upsert_inputs__pgn_upsert_plan(
        row,
        latest_hash,
        latest_version,
        hash_pgn,
    )
    return BaseDbStore.build_pgn_upsert_plan(inputs)
