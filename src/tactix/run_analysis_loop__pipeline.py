from __future__ import annotations

from tactix.analysis_progress_interval__pipeline import _analysis_progress_interval
from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import ProgressCallback
from tactix.process_analysis_position__pipeline import _process_analysis_position


def _run_analysis_loop(
    conn,
    settings: Settings,
    positions: list[dict[str, object]],
    resume_index: int,
    analysis_checkpoint_path,
    analysis_signature: str,
    progress: ProgressCallback | None,
    pg_conn,
    analysis_pg_enabled: bool,
) -> tuple[int, int]:
    total_positions = len(positions)
    progress_every = _analysis_progress_interval(total_positions)
    tactics_count = 0
    postgres_written = 0
    from tactix import StockfishEngine as pipeline_module  # noqa: PLC0415

    with pipeline_module.StockfishEngine(settings) as engine:
        for idx, pos in enumerate(positions):
            tactics_delta, postgres_delta = _process_analysis_position(
                conn,
                settings,
                engine,
                pos,
                idx,
                resume_index,
                analysis_checkpoint_path,
                analysis_signature,
                progress,
                total_positions,
                progress_every,
                pg_conn,
                analysis_pg_enabled,
            )
            tactics_count += tactics_delta
            postgres_written += postgres_delta
    return tactics_count, postgres_written
