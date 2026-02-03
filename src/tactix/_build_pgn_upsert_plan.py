from collections.abc import Mapping
from datetime import datetime
from typing import cast

from tactix.base_db_store import BaseDbStore, PgnUpsertPlan
from tactix.normalize_pgn import normalize_pgn


def _build_pgn_upsert_plan(
    row: Mapping[str, object],
    latest_hash: str | None,
    latest_version: int,
) -> PgnUpsertPlan | None:
    from tactix import postgres_store  # noqa: PLC0415

    pgn_text = str(row.get("pgn") or "")
    return BaseDbStore.build_pgn_upsert_plan(
        pgn_text=pgn_text,
        user=str(row.get("user") or ""),
        latest_hash=latest_hash,
        latest_version=latest_version,
        normalize_pgn=normalize_pgn,
        hash_pgn=postgres_store._hash_pgn_text,
        fetched_at=cast(datetime | None, row.get("fetched_at")),
        last_timestamp_ms=cast(int, row.get("last_timestamp_ms", 0)),
        cursor=row.get("cursor"),
    )
