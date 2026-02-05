"""Context for triggering Airflow daily sync."""

from __future__ import annotations

from dataclasses import dataclass

from tactix.config import Settings


@dataclass(frozen=True)
class AirflowDailySyncTriggerContext:
    """Context for triggering Airflow daily sync."""

    settings: Settings
    source: str | None
    profile: str | None
    backfill_start_ms: int | None = None
    backfill_end_ms: int | None = None
    triggered_at_ms: int | None = None
