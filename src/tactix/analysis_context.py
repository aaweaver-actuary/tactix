"""Dataclass containers for analysis pipeline contexts."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import ProgressCallback
from tactix.StockfishEngine import StockfishEngine


@dataclass(frozen=True)
class AnalysisRunInputs:
    """Grouped inputs for analysis runs."""

    positions: list[dict[str, object]]
    resume_index: int
    analysis_signature: str
    progress: ProgressCallback | None


class _AnalysisRunAccessors:
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
class AnalysisRunContext(_AnalysisRunAccessors):
    """Inputs for analysis runs that operate on stored positions."""

    conn: duckdb.DuckDBPyConnection
    settings: Settings
    run: AnalysisRunInputs


@dataclass(frozen=True)
class AnalysisAndMetricsContext(_AnalysisRunAccessors):
    """Inputs for analysis runs that also refresh metrics."""

    conn: duckdb.DuckDBPyConnection
    settings: Settings
    run: AnalysisRunInputs
    profile: str | None


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

    @property
    def pos(self) -> dict[str, object]:
        """Return the position payload."""
        return self.meta.pos

    @property
    def idx(self) -> int:
        """Return the position index."""
        return self.meta.idx

    @property
    def resume_index(self) -> int:
        """Return the resume index for analysis."""
        return self.meta.resume_index

    @property
    def total_positions(self) -> int:
        """Return the total positions count."""
        return self.meta.total_positions

    @property
    def progress_every(self) -> int:
        """Return the progress interval for analysis updates."""
        return self.meta.progress_every

    @property
    def analysis_checkpoint_path(self) -> object:
        """Return the analysis checkpoint path."""
        return self.persistence.analysis_checkpoint_path

    @property
    def analysis_signature(self) -> str:
        """Return the analysis signature."""
        return self.persistence.analysis_signature

    @property
    def pg_conn(self) -> object:
        """Return the Postgres connection for analysis writes."""
        return self.persistence.pg_conn

    @property
    def analysis_pg_enabled(self) -> bool:
        """Return whether Postgres analysis writes are enabled."""
        return self.persistence.analysis_pg_enabled
