"""Context for running the analysis loop."""

# pylint: disable=invalid-name

from dataclasses import dataclass

import duckdb

from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import ProgressCallback


@dataclass(frozen=True)
class AnalysisLoopContext:  # pylint: disable=too-many-instance-attributes
    """Inputs required to process an analysis loop."""

    conn: duckdb.DuckDBPyConnection
    settings: Settings
    positions: list[dict[str, object]]
    resume_index: int
    analysis_checkpoint_path: object
    analysis_signature: str
    progress: ProgressCallback | None
    pg_conn: object
    analysis_pg_enabled: bool
