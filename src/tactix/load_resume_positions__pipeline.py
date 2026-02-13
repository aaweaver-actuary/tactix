"""Load positions to resume analysis based on checkpoints."""

from __future__ import annotations

from tactix.analysis_signature__pipeline import _analysis_signature
from tactix.app.use_cases.pipeline_support import (
    _clear_analysis_checkpoint,
    _read_analysis_checkpoint,
)
from tactix.db.position_repository_provider import fetch_positions_for_games
from tactix.define_pipeline_state__pipeline import RESUME_INDEX_START, logger


def _load_resume_positions(
    conn,
    analysis_checkpoint_path,
    game_ids: list[str],
    source: str,
) -> tuple[list[dict[str, object]], int, str]:
    return _load_resume_context(conn, analysis_checkpoint_path, game_ids, source)


def _load_resume_context(
    conn,
    analysis_checkpoint_path,
    game_ids: list[str],
    source: str,
) -> tuple[list[dict[str, object]], int, str]:
    if not analysis_checkpoint_path.exists():
        return [], -1, ""
    positions_to_analyze = _fetch_positions_to_analyze(
        conn,
        analysis_checkpoint_path,
        game_ids,
    )
    if not positions_to_analyze:
        return [], -1, ""
    analysis_signature = _analysis_signature(
        game_ids,
        len(positions_to_analyze),
        source,
    )
    resume_index = _read_analysis_checkpoint(analysis_checkpoint_path, analysis_signature)
    if resume_index >= RESUME_INDEX_START:
        logger.info("Resuming analysis at index=%s for source=%s", resume_index, source)
        return positions_to_analyze, resume_index, analysis_signature
    _clear_analysis_checkpoint(analysis_checkpoint_path)
    return [], resume_index, analysis_signature


def _fetch_positions_to_analyze(
    conn,
    analysis_checkpoint_path,
    game_ids: list[str],
) -> list[dict[str, object]]:
    existing_positions = fetch_positions_for_games(conn, game_ids)
    if not existing_positions:
        _clear_analysis_checkpoint(analysis_checkpoint_path)
        return []
    return list(existing_positions)
