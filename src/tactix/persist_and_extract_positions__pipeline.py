from __future__ import annotations

from tactix.analysis_signature__pipeline import _analysis_signature
from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import GameRow, ProgressCallback
from tactix.emit_progress__pipeline import _emit_progress
from tactix.extract_positions_from_games__pipeline import _extract_positions_from_games
from tactix.persist_raw_pgns__pipeline import _persist_raw_pgns
from tactix.upsert_postgres_raw_pgns_if_enabled__pipeline import (
    _upsert_postgres_raw_pgns_if_enabled,
)


def _persist_and_extract_positions(
    conn,
    settings: Settings,
    games_to_process: list[GameRow],
    progress: ProgressCallback | None,
    profile: str | None,
    game_ids: list[str],
) -> tuple[list[dict[str, object]], str, tuple[int, int, int], int]:
    raw_pgns_inserted, raw_pgns_hashed, raw_pgns_matched = _persist_raw_pgns(
        conn,
        games_to_process,
        settings,
        progress,
        profile,
        delete_existing=True,
        emit_start=True,
    )
    postgres_raw_pgns_inserted = _upsert_postgres_raw_pgns_if_enabled(
        settings,
        games_to_process,
        progress,
        profile,
    )
    _emit_progress(
        progress,
        "extract_positions",
        source=settings.source,
        message="Extracting positions",
    )
    positions = _extract_positions_from_games(conn, games_to_process, settings)
    analysis_signature = _analysis_signature(game_ids, len(positions), settings.source)
    return (
        positions,
        analysis_signature,
        (raw_pgns_inserted, raw_pgns_hashed, raw_pgns_matched),
        postgres_raw_pgns_inserted,
    )
