"""Upsert raw PGNs into Postgres when enabled."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

import psycopg2

from tactix.app.use_cases.pipeline_support import _emit_progress
from tactix.config import Settings
from tactix.db.postgres_raw_pgn_repository import PostgresRawPgnRepository
from tactix.define_pipeline_state__pipeline import ProgressCallback, logger
from tactix.GameRow import GameRow
from tactix.init_pgn_schema import init_pgn_schema
from tactix.ops_event import OpsEvent
from tactix.postgres_connection import postgres_connection
from tactix.postgres_pgns_enabled import postgres_pgns_enabled
from tactix.record_ops_event import (
    record_ops_event,
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
                repo = PostgresRawPgnRepository(pg_conn)
                inserted = repo.upsert_raw_pgns(
                    cast(list[Mapping[str, object]], games_to_process),
                )
            except psycopg2.Error as exc:
                logger.warning("Postgres raw PGN upsert failed: %s", exc)
    _emit_progress(
        progress,
        "postgres_raw_pgns_persisted",
        source=settings.source,
        inserted=inserted,
        total=len(games_to_process),
    )
    record_ops_event(
        OpsEvent(
            settings=settings,
            component="ingestion",
            event_type="postgres_raw_pgns_persisted",
            source=settings.source,
            profile=profile,
            metadata={
                "inserted": inserted,
                "total": len(games_to_process),
            },
        )
    )
    return inserted
