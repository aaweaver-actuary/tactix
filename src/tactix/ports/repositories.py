"""Repository port interfaces for database access boundaries."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Protocol


class RawPgnRepository(Protocol):
    """Repository interface for raw PGN persistence and lookup."""

    def upsert_raw_pgns(self, rows: Iterable[Mapping[str, object]]) -> int:
        """Insert or update raw PGN rows and return insert count."""

    def fetch_latest_pgn_hashes(
        self,
        game_ids: list[str],
        source: str,
    ) -> dict[str, str]:
        """Return latest hashes for the provided game ids."""

    def fetch_latest_raw_pgns(self, source: str, limit: int) -> list[dict[str, object]]:
        """Return the latest raw PGN rows for the given source."""

    def fetch_raw_pgns_summary(self, source: str | None = None) -> dict[str, object]:
        """Return the raw PGN summary payload."""


class GameRepository(RawPgnRepository, Protocol):
    """Alias interface for raw PGN-backed game storage."""


class PositionRepository(Protocol):
    """Repository interface for position storage."""

    def fetch_position_counts(self, game_ids: list[str], source: str) -> dict[str, int]:
        """Return per-game position counts for the provided games."""

    def fetch_positions_for_games(self, game_ids: list[str]) -> list[dict[str, object]]:
        """Return stored positions for the provided games."""

    def insert_positions(self, positions: list[Mapping[str, object]]) -> list[int]:
        """Insert position rows and return new ids."""


class ConversionRepository(Protocol):
    """Repository interface for conversion/outcome persistence."""

    def insert_tactic_outcomes(self, rows: list[Mapping[str, object]]) -> list[int]:
        """Insert outcome rows and return ids."""

    def upsert_tactic_with_outcome(
        self,
        tactic_row: Mapping[str, object],
        outcome_row: Mapping[str, object],
    ) -> int:
        """Upsert a tactic with its outcome and return the tactic id."""


class PracticeQueueRepository(Protocol):
    """Repository interface for practice queue retrieval."""

    def fetch_practice_tactic(self, tactic_id: int) -> dict[str, object] | None:
        """Return the tactic payload for a practice item."""

    def fetch_practice_queue(
        self,
        source: str,
        include_failed_attempt: bool = False,
    ) -> list[dict[str, object]]:
        """Return practice queue items for the given source."""


class TacticRepository(ConversionRepository, PracticeQueueRepository, Protocol):
    """Repository interface for tactics and practice workflows."""

    def insert_tactics(self, rows: list[Mapping[str, object]]) -> list[int]:
        """Insert tactic rows and return ids."""

    def grade_practice_attempt(
        self,
        payload: Mapping[str, object],
    ) -> dict[str, object]:
        """Grade a practice attempt payload."""

    def record_training_attempt(self, payload: Mapping[str, object]) -> int:
        """Insert a training attempt and return its id."""

    def fetch_game_detail(self, game_id: str) -> dict[str, object] | None:
        """Return detailed game payloads when available."""


class DashboardRepository(Protocol):
    """Repository interface for dashboard queries."""

    def fetch_pipeline_table_counts(
        self,
        query,
        **kwargs: object,
    ) -> dict[str, int]:
        """Return pipeline table counts for the dashboard."""

    def fetch_opportunity_motif_counts(
        self,
        query,
        **kwargs: object,
    ) -> dict[str, int]:
        """Return opportunity motif counts for the dashboard."""

    def fetch_metrics(self, query, **kwargs: object) -> dict[str, object]:
        """Return aggregated metrics for the dashboard."""

    def fetch_recent_games(self, query, **kwargs: object) -> list[dict[str, object]]:
        """Return recent games for the dashboard."""

    def fetch_recent_positions(self, query, **kwargs: object) -> list[dict[str, object]]:
        """Return recent positions for the dashboard."""

    def fetch_recent_tactics(self, query, **kwargs: object) -> list[dict[str, object]]:
        """Return recent tactics for the dashboard."""


class MetricsRepository(Protocol):
    """Repository interface for metrics updates."""

    def update_metrics_summary(self) -> None:
        """Update the metrics summary tables."""
