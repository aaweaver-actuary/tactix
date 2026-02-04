"""Load positions to resume analysis based on checkpoints."""

from __future__ import annotations

from tactix.analysis_signature__pipeline import _analysis_signature
from tactix.clear_analysis_checkpoint__pipeline import _clear_analysis_checkpoint
from tactix.db.duckdb_store import fetch_positions_for_games
from tactix.define_pipeline_state__pipeline import RESUME_INDEX_START, logger
from tactix.read_analysis_checkpoint__pipeline import _read_analysis_checkpoint


def _load_resume_positions(
    conn,
    analysis_checkpoint_path,
    game_ids: list[str],
    source: str,
) -> tuple[list[dict[str, object]], int, str]:
    positions: list[dict[str, object]] = []
    resume_index = -1
    analysis_signature = ""
    if analysis_checkpoint_path.exists():
        existing_positions = fetch_positions_for_games(conn, game_ids)
        if existing_positions:
            analysis_signature = _analysis_signature(game_ids, len(existing_positions), source)
            resume_index = _read_analysis_checkpoint(analysis_checkpoint_path, analysis_signature)
            if resume_index >= RESUME_INDEX_START:
                logger.info("Resuming analysis at index=%s for source=%s", resume_index, source)
                positions = existing_positions
            else:
                _clear_analysis_checkpoint(analysis_checkpoint_path)
        else:
            _clear_analysis_checkpoint(analysis_checkpoint_path)
    return positions, resume_index, analysis_signature
