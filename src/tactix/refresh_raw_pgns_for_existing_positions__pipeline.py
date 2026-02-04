"""Refresh raw PGNs for existing positions."""

from __future__ import annotations

from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import GameRow, ProgressCallback
from tactix.persist_raw_pgns__pipeline import PersistRawPgnsContext, _persist_raw_pgns
from tactix.upsert_postgres_raw_pgns_if_enabled__pipeline import (
    _upsert_postgres_raw_pgns_if_enabled,
)


def _refresh_raw_pgns_for_existing_positions(
    conn,
    settings: Settings,
    games_to_process: list[GameRow],
    progress: ProgressCallback | None,
    profile: str | None,
) -> tuple[tuple[int, int, int], int]:
    raw_pgns_inserted, raw_pgns_hashed, raw_pgns_matched = _persist_raw_pgns(
        PersistRawPgnsContext(
            conn=conn,
            games_to_process=games_to_process,
            settings=settings,
            progress=progress,
            profile=profile,
            delete_existing=False,
            emit_start=False,
        )
    )
    postgres_raw_pgns_inserted = _upsert_postgres_raw_pgns_if_enabled(
        settings,
        games_to_process,
        progress,
        profile,
    )
    return (raw_pgns_inserted, raw_pgns_hashed, raw_pgns_matched), postgres_raw_pgns_inserted
