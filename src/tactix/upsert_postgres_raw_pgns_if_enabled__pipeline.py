from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from tactix.config import Settings
from tactix.emit_progress__pipeline import _emit_progress
from tactix.pipeline_state__pipeline import GameRow, ProgressCallback, logger
from tactix.postgres_store import (
    init_pgn_schema,
    postgres_connection,
    postgres_pgns_enabled,
    record_ops_event,
    upsert_postgres_raw_pgns,
)


def _upsert_postgres_raw_pgns_if_enabled(
    settings: Settings,
    games_to_process: list[GameRow],
    progress: ProgressCallback | None,
    profile: str | None,
) -> int:
    if not postgres_pgns_enabled(settings):
        return 0
    inserted = 0
    with postgres_connection(settings) as pg_conn:
        if pg_conn is None:
            logger.warning("Postgres raw PGN mirror enabled but connection unavailable")
        else:
            init_pgn_schema(pg_conn)
            try:
                inserted = upsert_postgres_raw_pgns(
                    pg_conn,
                    cast(list[Mapping[str, object]], games_to_process),
                )
            except Exception as exc:
                logger.warning("Postgres raw PGN upsert failed: %s", exc)
    _emit_progress(
        progress,
        "postgres_raw_pgns_persisted",
        source=settings.source,
        inserted=inserted,
        total=len(games_to_process),
    )
    record_ops_event(
        settings,
        component="ingestion",
        event_type="postgres_raw_pgns_persisted",
        source=settings.source,
        profile=profile,
        metadata={
            "inserted": inserted,
            "total": len(games_to_process),
        },
    )
    return inserted
