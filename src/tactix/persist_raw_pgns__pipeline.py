from __future__ import annotations

from tactix.config import Settings
from tactix.db.duckdb_store import delete_game_rows, upsert_raw_pgns
from tactix.define_pipeline_state__pipeline import GameRow, ProgressCallback
from tactix.emit_progress__pipeline import _emit_progress
from tactix.record_ops_event import record_ops_event
from tactix.validate_raw_pgn_hashes__pipeline import _validate_raw_pgn_hashes


def _persist_raw_pgns(
    conn,
    games_to_process: list[GameRow],
    settings: Settings,
    progress: ProgressCallback | None,
    profile: str | None,
    *,
    delete_existing: bool,
    emit_start: bool,
) -> tuple[int, int, int]:
    if emit_start:
        _emit_progress(
            progress,
            "raw_pgns",
            source=settings.source,
            message="Persisting raw PGNs",
        )
    if delete_existing:
        delete_game_rows(conn, [game["game_id"] for game in games_to_process])
    raw_pgns_inserted = upsert_raw_pgns(conn, games_to_process)
    hash_metrics = _validate_raw_pgn_hashes(conn, games_to_process, settings.source)
    raw_pgns_hashed = hash_metrics["computed"]
    raw_pgns_matched = hash_metrics["matched"]
    _emit_progress(
        progress,
        "raw_pgns_persisted",
        source=settings.source,
        inserted=raw_pgns_inserted,
        total=len(games_to_process),
    )
    _emit_progress(
        progress,
        "raw_pgns_hashed",
        source=settings.source,
        computed=raw_pgns_hashed,
        matched=raw_pgns_matched,
    )
    record_ops_event(
        settings,
        component="ingestion",
        event_type="raw_pgns_persisted",
        source=settings.source,
        profile=profile,
        metadata={
            "inserted": raw_pgns_inserted,
            "computed": raw_pgns_hashed,
            "matched": raw_pgns_matched,
            "total": len(games_to_process),
        },
    )
    return raw_pgns_inserted, raw_pgns_hashed, raw_pgns_matched
