"""Persist raw PGNs and extract positions for analysis."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from tactix.analysis_signature__pipeline import _analysis_signature
from tactix.app.use_cases.pipeline_support import _emit_progress
from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import ProgressCallback
from tactix.extract_positions_from_games__pipeline import _extract_positions_from_games
from tactix.GameRow import GameRow
from tactix.persist_raw_pgns__pipeline import PersistRawPgnsContext, _persist_raw_pgns
from tactix.upsert_postgres_raw_pgns_if_enabled__pipeline import (
    _upsert_postgres_raw_pgns_if_enabled,
)


@dataclass(frozen=True)
class PersistAndExtractPositionsContext:
    """Context for persisting raw PGNs and extracting positions."""

    conn: duckdb.DuckDBPyConnection
    settings: Settings
    games_to_process: list[GameRow]
    progress: ProgressCallback | None
    profile: str | None
    game_ids: list[str]


def _persist_and_extract_positions(
    context: PersistAndExtractPositionsContext,
) -> tuple[list[dict[str, object]], str, tuple[int, int, int], int]:
    """Persist raw PGNs, extract positions, and return metrics."""
    raw_pgns_inserted, raw_pgns_hashed, raw_pgns_matched = _persist_raw_pgns(
        PersistRawPgnsContext(
            conn=context.conn,
            games_to_process=context.games_to_process,
            settings=context.settings,
            progress=context.progress,
            profile=context.profile,
            delete_existing=True,
            emit_start=True,
        )
    )
    postgres_raw_pgns_inserted = _upsert_postgres_raw_pgns_if_enabled(
        context.settings,
        context.games_to_process,
        context.progress,
        context.profile,
    )
    _emit_progress(
        context.progress,
        "extract_positions",
        source=context.settings.source,
        message="Extracting positions",
    )
    positions = _extract_positions_from_games(
        context.conn,
        context.games_to_process,
        context.settings,
    )
    analysis_signature = _analysis_signature(
        context.game_ids,
        len(positions),
        context.settings.source,
    )
    return (
        positions,
        analysis_signature,
        (raw_pgns_inserted, raw_pgns_hashed, raw_pgns_matched),
        postgres_raw_pgns_inserted,
    )
