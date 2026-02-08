"""Persist raw PGNs into the database."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from tactix.app.use_cases.pipeline_support import _emit_progress
from tactix.build_games_table_row__pipeline import _build_games_table_row
from tactix.config import Settings
from tactix.db.delete_game_rows import delete_game_rows
from tactix.db.game_repository_provider import upsert_games
from tactix.db.raw_pgn_repository_provider import raw_pgn_repository
from tactix.define_pipeline_state__pipeline import ProgressCallback
from tactix.GameRow import GameRow
from tactix.ops_event import OpsEvent
from tactix.record_ops_event import record_ops_event
from tactix.validate_raw_pgn_hashes__pipeline import _validate_raw_pgn_hashes


@dataclass(frozen=True)
class PersistRawPgnsContext:
    """Context for persisting raw PGNs."""

    conn: duckdb.DuckDBPyConnection
    games_to_process: list[GameRow]
    settings: Settings
    progress: ProgressCallback | None
    profile: str | None
    delete_existing: bool
    emit_start: bool


def _persist_raw_pgns(context: PersistRawPgnsContext) -> tuple[int, int, int]:
    """Persist raw PGNs and return insert/hash metrics."""
    repository = raw_pgn_repository(context.conn)
    if context.emit_start:
        _emit_progress(
            context.progress,
            "raw_pgns",
            source=context.settings.source,
            message="Persisting raw PGNs",
        )
    if context.delete_existing:
        delete_game_rows(
            context.conn,
            [game["game_id"] for game in context.games_to_process],
        )
    raw_pgns_inserted = repository.upsert_raw_pgns(context.games_to_process)
    upsert_games(
        context.conn,
        [_build_games_table_row(game) for game in context.games_to_process],
    )
    hash_metrics = _validate_raw_pgn_hashes(
        context.games_to_process,
        context.settings.source,
        repository.fetch_latest_pgn_hashes,
    )
    raw_pgns_hashed = hash_metrics["computed"]
    raw_pgns_matched = hash_metrics["matched"]
    _emit_progress(
        context.progress,
        "raw_pgns_persisted",
        source=context.settings.source,
        inserted=raw_pgns_inserted,
        total=len(context.games_to_process),
    )
    _emit_progress(
        context.progress,
        "raw_pgns_hashed",
        source=context.settings.source,
        computed=raw_pgns_hashed,
        matched=raw_pgns_matched,
    )
    record_ops_event(
        OpsEvent(
            settings=context.settings,
            component="ingestion",
            event_type="raw_pgns_persisted",
            source=context.settings.source,
            profile=context.profile,
            metadata={
                "inserted": raw_pgns_inserted,
                "computed": raw_pgns_hashed,
                "matched": raw_pgns_matched,
                "total": len(context.games_to_process),
            },
        )
    )
    return raw_pgns_inserted, raw_pgns_hashed, raw_pgns_matched
