"""Dataclass containers for analysis pipeline contexts."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from tactix.config import Settings
from tactix.ProgressCallback import ProgressCallback
from tactix.StockfishEngine import StockfishEngine


@dataclass(frozen=True)
class AnalysisRunInputs:
    """Grouped inputs for analysis runs."""

    positions: list[dict[str, object]]
    resume_index: int
    analysis_signature: str
    progress: ProgressCallback | None


@dataclass(frozen=True)
class AnalysisRunContext:
    """Inputs for analysis runs that operate on stored positions."""

    conn: duckdb.DuckDBPyConnection
    settings: Settings
    run: AnalysisRunInputs

    @property
    def positions(self) -> list[dict[str, object]]:
        """Return the positions to analyze."""
        return self.run.positions

    @property
    def resume_index(self) -> int:
        """Return the resume index."""
        return self.run.resume_index

    @property
    def analysis_signature(self) -> str:
        """Return the analysis signature."""
        return self.run.analysis_signature

    @property
    def progress(self) -> ProgressCallback | None:
        """Return the progress callback."""
        return self.run.progress


@dataclass(frozen=True)
class AnalysisAndMetricsContext:
    """Inputs for analysis runs that also refresh metrics."""

    conn: duckdb.DuckDBPyConnection
    settings: Settings
    run: AnalysisRunInputs
    profile: str | None

    @property
    def positions(self) -> list[dict[str, object]]:
        """Return the positions to analyze."""
        return self.run.positions

    @property
    def resume_index(self) -> int:
        """Return the resume index."""
        return self.run.resume_index

    @property
    def analysis_signature(self) -> str:
        """Return the analysis signature."""
        return self.run.analysis_signature

    @property
    def progress(self) -> ProgressCallback | None:
        """Return the progress callback."""
        return self.run.progress


@dataclass(frozen=True)
class AnalysisPositionMeta:
    """Position-specific metadata for analysis processing."""

    pos: dict[str, object]
    idx: int
    resume_index: int
    total_positions: int
    progress_every: int


@dataclass(frozen=True)
class AnalysisPositionPersistence:
    """Persistence-related dependencies for analysis processing."""

    analysis_checkpoint_path: object
    analysis_signature: str
    pg_conn: object
    analysis_pg_enabled: bool


@dataclass(frozen=True)
class AnalysisPositionContext:
    """Combined context for processing a single analysis position."""

    conn: duckdb.DuckDBPyConnection
    settings: Settings
    engine: StockfishEngine
    meta: AnalysisPositionMeta
    persistence: AnalysisPositionPersistence
    progress: ProgressCallback | None
