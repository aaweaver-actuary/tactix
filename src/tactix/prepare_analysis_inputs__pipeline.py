from __future__ import annotations

from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import (
    AnalysisPrepResult,
    GameRow,
    ProgressCallback,
)
from tactix.load_resume_positions__pipeline import _load_resume_positions
from tactix.persist_and_extract_positions__pipeline import (
    PersistAndExtractPositionsContext,
    _persist_and_extract_positions,
)
from tactix.refresh_raw_pgns_for_existing_positions__pipeline import (
    _refresh_raw_pgns_for_existing_positions,
)


def _prepare_analysis_inputs(
    conn,
    settings: Settings,
    games_to_process: list[GameRow],
    progress: ProgressCallback | None,
    profile: str | None,
) -> AnalysisPrepResult:
    game_ids = [game["game_id"] for game in games_to_process]
    analysis_checkpoint_path = settings.analysis_checkpoint_path
    positions, resume_index, analysis_signature = _load_resume_positions(
        conn, analysis_checkpoint_path, game_ids, settings.source
    )
    if positions:
        (raw_pgns_inserted, raw_pgns_hashed, raw_pgns_matched), postgres_raw_pgns_inserted = (
            _refresh_raw_pgns_for_existing_positions(
                conn,
                settings,
                games_to_process,
                progress,
                profile,
            )
        )
        return AnalysisPrepResult(
            positions=positions,
            resume_index=resume_index,
            analysis_signature=analysis_signature,
            raw_pgns_inserted=raw_pgns_inserted,
            raw_pgns_hashed=raw_pgns_hashed,
            raw_pgns_matched=raw_pgns_matched,
            postgres_raw_pgns_inserted=postgres_raw_pgns_inserted,
        )

    positions, analysis_signature, raw_metrics, postgres_raw_pgns_inserted = (
        _persist_and_extract_positions(
            PersistAndExtractPositionsContext(
                conn=conn,
                settings=settings,
                games_to_process=games_to_process,
                progress=progress,
                profile=profile,
                game_ids=game_ids,
            )
        )
    )
    raw_pgns_inserted, raw_pgns_hashed, raw_pgns_matched = raw_metrics
    return AnalysisPrepResult(
        positions=positions,
        resume_index=resume_index,
        analysis_signature=analysis_signature,
        raw_pgns_inserted=raw_pgns_inserted,
        raw_pgns_hashed=raw_pgns_hashed,
        raw_pgns_matched=raw_pgns_matched,
        postgres_raw_pgns_inserted=postgres_raw_pgns_inserted,
    )
