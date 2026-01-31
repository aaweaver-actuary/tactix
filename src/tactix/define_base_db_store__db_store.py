from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import cast

from tactix.config import Settings
from tactix.define_base_db_store_context__db_store import BaseDbStoreContext
from tactix.define_outcome_insert_plan__db_store import OutcomeInsertPlan
from tactix.define_pgn_upsert_plan__db_store import PgnUpsertPlan
from tactix.define_tactic_insert_plan__db_store import TacticInsertPlan
from tactix.is_latest_hash__db_store import _is_latest_hash
from tactix.prepare_pgn__chess import extract_pgn_metadata
from tactix.resolve_pgn_hash__db_store import _resolve_pgn_hash
from tactix.resolve_timestamp__db_store import _resolve_timestamp
from tactix.utils import hash


class BaseDbStore:
    """Base class for database stores.

    Subclasses are expected to implement dashboard-specific behavior.
    """

    def __init__(self, context: BaseDbStoreContext) -> None:
        """Initialize the store with shared context.

        Args:
            context: Base context containing settings and logger.
        """

        self._context = context

    @property
    def settings(self) -> Settings:
        """Expose the settings from the context."""

        return self._context.settings

    @property
    def logger(self) -> logging.Logger:
        """Expose the logger from the context."""

        return self._context.logger

    @staticmethod
    def extract_pgn_metadata(pgn: str, user: str) -> Mapping[str, object]:
        """Extract PGN metadata using shared utilities."""

        return extract_pgn_metadata(pgn, user)

    @staticmethod
    def hash_pgn(pgn: str) -> str:
        """Return the normalized hash for PGN content."""

        return hash(pgn)

    @staticmethod
    def build_pgn_upsert_plan(
        *,
        pgn_text: str,
        user: str,
        latest_hash: str | None,
        latest_version: int,
        normalize_pgn: Callable[[str], str] | None = None,
        hash_pgn: Callable[[str], str] | None = None,
        fetched_at: datetime | None = None,
        ingested_at: datetime | None = None,
        last_timestamp_ms: int = 0,
        cursor: object | None = None,
    ) -> PgnUpsertPlan | None:
        normalized, pgn_hash = _resolve_pgn_hash(pgn_text, normalize_pgn, hash_pgn)
        if _is_latest_hash(latest_hash, pgn_hash):
            return None
        metadata = extract_pgn_metadata(pgn_text, user)
        return PgnUpsertPlan(
            pgn_text=pgn_text,
            pgn_hash=pgn_hash,
            pgn_version=latest_version + 1,
            normalized_pgn=normalized,
            metadata=metadata,
            fetched_at=_resolve_timestamp(fetched_at),
            ingested_at=_resolve_timestamp(ingested_at),
            last_timestamp_ms=last_timestamp_ms,
            cursor=cursor,
        )

    @staticmethod
    def require_position_id(
        tactic_row: Mapping[str, object],
        error_message: str,
    ) -> object:
        position_id = tactic_row.get("position_id")
        if position_id is None:
            raise ValueError(error_message)
        return position_id

    @staticmethod
    def build_tactic_insert_plan(
        *,
        game_id: object,
        position_id: object,
        tactic_row: Mapping[str, object],
    ) -> TacticInsertPlan:
        return TacticInsertPlan(
            game_id=game_id,
            position_id=position_id,
            motif=cast(str, tactic_row.get("motif", "unknown")),
            severity=tactic_row.get("severity", 0.0),
            best_uci=tactic_row.get("best_uci", ""),
            best_san=tactic_row.get("best_san"),
            explanation=tactic_row.get("explanation"),
            eval_cp=tactic_row.get("eval_cp", 0),
        )

    @staticmethod
    def build_outcome_insert_plan(
        outcome_row: Mapping[str, object],
    ) -> OutcomeInsertPlan:
        return OutcomeInsertPlan(
            result=cast(str, outcome_row.get("result", "unclear")),
            user_uci=outcome_row.get("user_uci", ""),
            eval_delta=outcome_row.get("eval_delta", 0),
        )

    def _now_utc(self) -> datetime:
        """Return the current UTC time."""

        return datetime.now(UTC)

    def get_dashboard_payload(
        self,
        source: str | None = None,
        motif: str | None = None,
        rating_bucket: str | None = None,
        time_control: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, object]:
        """Build a dashboard payload for the store implementation."""

        raise NotImplementedError("Subclasses must implement get_dashboard_payload")
