"""Build PGN upsert plans from raw rows."""

import importlib
from collections.abc import Mapping
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


def _build_pgn_upsert_plan(
    row: Mapping[str, object],
    latest_hash: str | None,
    latest_version: int,
) -> PgnUpsertPlan | None:
    """Return a PGN upsert plan for the given raw row."""
    postgres_store = _resolve_postgres_store()
    if postgres_store is None:
        hash_pgn = _hash_pgn_text
    else:
        hash_pgn = getattr(postgres_store, "_hash_pgn_text", _hash_pgn_text)
    pgn_text = str(row.get("pgn") or "")
    return BaseDbStore.build_pgn_upsert_plan(
        PgnUpsertInputs(
            pgn_text=pgn_text,
            user=str(row.get("user") or ""),
            latest_hash=latest_hash,
            latest_version=latest_version,
            hashing=PgnUpsertHashing(
                normalize_pgn=None,
                hash_pgn=hash_pgn,
            ),
            timestamps=PgnUpsertTimestamps(
                fetched_at=cast(datetime | None, row.get("fetched_at")),
                ingested_at=cast(datetime | None, row.get("ingested_at")),
                last_timestamp_ms=cast(int, row.get("last_timestamp_ms", 0)),
            ),
            cursor=row.get("cursor"),
        )
    )
