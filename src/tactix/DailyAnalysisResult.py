from dataclasses import dataclass


@dataclass(slots=True)
class DailyAnalysisResult:
    """Summary of a daily analysis run."""

    total_positions: int
    tactics_count: int
    postgres_written: int
    postgres_synced: int
    metrics_version: int
