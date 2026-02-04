"""Build PGN upsert plans from raw rows."""

from collections.abc import Mapping
from datetime import datetime
from importlib import import_module
from typing import cast

from tactix._hash_pgn_text import _hash_pgn_text
from tactix.base_db_store import BaseDbStore, PgnUpsertPlan
from tactix.normalize_pgn import normalize_pgn
from tactix.PgnUpsertInputs import PgnUpsertInputs


def _build_pgn_upsert_plan(
    row: Mapping[str, object],
    latest_hash: str | None,
    latest_version: int,
) -> PgnUpsertPlan | None:
    """Return a PGN upsert plan for the given raw row."""
    pgn_text = str(row.get("pgn") or "")
    postgres_store = import_module("tactix.postgres_store")
    hash_pgn = getattr(postgres_store, "_hash_pgn_text", _hash_pgn_text)
    return BaseDbStore.build_pgn_upsert_plan(
        PgnUpsertInputs(
            pgn_text=pgn_text,
            user=str(row.get("user") or ""),
            latest_hash=latest_hash,
            latest_version=latest_version,
            normalize_pgn=normalize_pgn,
            hash_pgn=hash_pgn,
            fetched_at=cast(datetime | None, row.get("fetched_at")),
            last_timestamp_ms=cast(int, row.get("last_timestamp_ms", 0)),
            cursor=row.get("cursor"),
        )
    )
