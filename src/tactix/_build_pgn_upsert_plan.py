"""Build PGN upsert plans from raw rows."""

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import cast

from tactix.define_base_db_store__db_store import BaseDbStore
from tactix.PgnUpsertInputs import PgnUpsertHashing, PgnUpsertInputs, PgnUpsertTimestamps
from tactix.PgnUpsertPlan import PgnUpsertPlan


def _resolve_hash_pgn__pgn_upsert_plan() -> Callable[[str], str]:
    return BaseDbStore.hash_pgn


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
    hash_pgn = _resolve_hash_pgn__pgn_upsert_plan()
    inputs = _build_pgn_upsert_inputs__pgn_upsert_plan(
        row,
        latest_hash,
        latest_version,
        hash_pgn,
    )
    return BaseDbStore.build_pgn_upsert_plan(inputs)
