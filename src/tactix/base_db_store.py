from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import logging
from typing import Callable, Mapping, cast

from tactix.config import Settings
from tactix.pgn_utils import extract_pgn_metadata


@dataclass(slots=True)
class BaseDbStoreContext:
    """Shared context for database stores.

    Attributes:
        settings: Application settings for store configuration.
        logger: Logger for store-specific messages.
    """

    settings: Settings
    logger: logging.Logger


@dataclass(slots=True)
class PgnUpsertPlan:
    pgn_text: str
    pgn_hash: str
    pgn_version: int
    normalized_pgn: str | None
    metadata: Mapping[str, object]
    fetched_at: datetime
    ingested_at: datetime
    last_timestamp_ms: int
    cursor: object | None


@dataclass(slots=True)
class TacticInsertPlan:
    game_id: object
    position_id: object
    motif: str
    severity: object
    best_uci: object
    best_san: object
    explanation: object
    eval_cp: object


@dataclass(slots=True)
class OutcomeInsertPlan:
    result: str
    user_uci: object
    eval_delta: object


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
    def hash_pgn_text(pgn: str) -> str:
        """Hash PGN text using SHA-256."""

        return hashlib.sha256(pgn.encode("utf-8")).hexdigest()

    @staticmethod
    def extract_pgn_metadata(pgn: str, user: str) -> Mapping[str, object]:
        """Extract PGN metadata using shared utilities."""

        return extract_pgn_metadata(pgn, user)

    def _now_utc(self) -> datetime:
        """Return the current UTC time."""

        return datetime.now(timezone.utc)

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
        normalized = normalize_pgn(pgn_text) if normalize_pgn else None
        hash_input = normalized or pgn_text
        hash_fn = hash_pgn or BaseDbStore.hash_pgn_text
        pgn_hash = hash_fn(hash_input)
        if latest_hash == pgn_hash:
            return None
        metadata = BaseDbStore.extract_pgn_metadata(pgn_text, user)
        now = datetime.now(timezone.utc)
        return PgnUpsertPlan(
            pgn_text=pgn_text,
            pgn_hash=pgn_hash,
            pgn_version=latest_version + 1,
            normalized_pgn=normalized,
            metadata=metadata,
            fetched_at=fetched_at or now,
            ingested_at=ingested_at or now,
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
