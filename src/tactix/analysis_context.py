from __future__ import annotations

from dataclasses import dataclass

import duckdb

from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import ProgressCallback
from tactix.StockfishEngine import StockfishEngine


@dataclass(frozen=True)
class AnalysisRunContext:
    conn: duckdb.DuckDBPyConnection
    settings: Settings
    positions: list[dict[str, object]]
    resume_index: int
    analysis_signature: str
    progress: ProgressCallback | None


@dataclass(frozen=True)
class AnalysisAndMetricsContext:
    conn: duckdb.DuckDBPyConnection
    settings: Settings
    positions: list[dict[str, object]]
    resume_index: int
    analysis_signature: str
    progress: ProgressCallback | None
    profile: str | None


@dataclass(frozen=True)
class AnalysisPositionContext:
    conn: duckdb.DuckDBPyConnection
    settings: Settings
    engine: StockfishEngine
    pos: dict[str, object]
    idx: int
    resume_index: int
    analysis_checkpoint_path: object
    analysis_signature: str
    progress: ProgressCallback | None
    total_positions: int
    progress_every: int
    pg_conn: object
    analysis_pg_enabled: bool
