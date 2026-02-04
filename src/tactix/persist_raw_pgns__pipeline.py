"""Persist raw PGNs into the database."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from tactix.app.use_cases.pipeline_support import _emit_progress
from tactix.config import Settings
from tactix.db.duckdb_store import delete_game_rows, upsert_raw_pgns
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
    raw_pgns_inserted = upsert_raw_pgns(context.conn, context.games_to_process)
    hash_metrics = _validate_raw_pgn_hashes(
        context.conn,
        context.games_to_process,
        context.settings.source,
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
