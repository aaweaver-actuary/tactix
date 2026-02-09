"""Base database store interface and helpers."""

# pylint: disable=redefined-builtin

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import cast

from tactix.config import Settings
from tactix.dashboard_query import DashboardQuery
from tactix.define_base_db_store_context__db_store import BaseDbStoreContext
from tactix.define_outcome_insert_plan__db_store import OutcomeInsertPlan
from tactix.define_tactic_insert_plan__db_store import TacticInsertPlan
from tactix.extract_pgn_metadata import extract_pgn_metadata
from tactix.is_latest_hash__db_store import _is_latest_hash
from tactix.PgnUpsertInputs import PgnUpsertHashing, PgnUpsertInputs, PgnUpsertTimestamps
from tactix.PgnUpsertPlan import PgnUpsertPlan
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
    def _resolve_pgn_upsert_inputs(
        inputs: PgnUpsertInputs | None,
        legacy: dict[str, object],
    ) -> PgnUpsertInputs:
        if inputs is not None:
            if legacy:
                raise TypeError(f"Unexpected keyword arguments: {', '.join(sorted(legacy))}")
            return inputs
        values = BaseDbStore._extract_pgn_upsert_values(legacy)
        return BaseDbStore._build_pgn_upsert_inputs(values)

    @staticmethod
    def _extract_pgn_upsert_values(legacy: dict[str, object]) -> dict[str, object]:
        defaults: dict[str, object] = {
            "pgn_text": None,
            "user": None,
            "latest_hash": None,
            "latest_version": None,
            "normalize_pgn": None,
            "hash_pgn": None,
            "fetched_at": None,
            "ingested_at": None,
            "last_timestamp_ms": 0,
            "cursor": None,
        }
        values = {key: legacy.pop(key, default) for key, default in defaults.items()}
        if legacy:
            raise TypeError(f"Unexpected keyword arguments: {', '.join(sorted(legacy))}")
        return values

    @staticmethod
    def _build_pgn_upsert_inputs(values: dict[str, object]) -> PgnUpsertInputs:
        if values["pgn_text"] is None or values["user"] is None or values["latest_version"] is None:
            raise TypeError("pgn_text, user, and latest_version are required")
        return PgnUpsertInputs(
            pgn_text=cast(str, values["pgn_text"]),
            user=cast(str, values["user"]),
            latest_hash=cast(str | None, values["latest_hash"]),
            latest_version=cast(int, values["latest_version"]),
            hashing=PgnUpsertHashing(
                normalize_pgn=cast(Callable[[str], str] | None, values["normalize_pgn"]),
                hash_pgn=cast(Callable[[str], str] | None, values["hash_pgn"]),
            ),
            timestamps=PgnUpsertTimestamps(
                fetched_at=cast(datetime | None, values["fetched_at"]),
                ingested_at=cast(datetime | None, values["ingested_at"]),
                last_timestamp_ms=cast(int, values["last_timestamp_ms"]),
            ),
            cursor=values["cursor"],
        )

    @staticmethod
    def build_pgn_upsert_plan(
        inputs: PgnUpsertInputs | None = None,
        **legacy: object,
    ) -> PgnUpsertPlan | None:
        """Build an upsert plan for PGN content when needed."""
        inputs = BaseDbStore._resolve_pgn_upsert_inputs(inputs, legacy)
        normalized, pgn_hash = _resolve_pgn_hash(
            inputs.pgn_text,
            inputs.normalize_pgn,
            inputs.hash_pgn,
        )
        if _is_latest_hash(inputs.latest_hash, pgn_hash):
            return None
        metadata = extract_pgn_metadata(inputs.pgn_text, inputs.user)
        return PgnUpsertPlan(
            pgn_text=inputs.pgn_text,
            pgn_hash=pgn_hash,
            pgn_version=inputs.latest_version + 1,
            normalized_pgn=normalized,
            metadata=metadata,
            fetched_at=_resolve_timestamp(inputs.fetched_at),
            ingested_at=_resolve_timestamp(inputs.ingested_at),
            last_timestamp_ms=inputs.last_timestamp_ms,
            cursor=inputs.cursor,
        )

    @staticmethod
    def require_position_id(
        tactic_row: Mapping[str, object],
        error_message: str,
    ) -> object:
        """Return the position id or raise a ValueError."""
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
        """Build a tactic insert plan from a row mapping."""
        return TacticInsertPlan(
            game_id=game_id,
            position_id=position_id,
            motif=cast(str, tactic_row.get("motif", "unknown")),
            severity=tactic_row.get("severity", 0.0),
            best_uci=tactic_row.get("best_uci", ""),
            tactic_piece=tactic_row.get("tactic_piece"),
            mate_type=tactic_row.get("mate_type"),
            best_san=tactic_row.get("best_san"),
            explanation=tactic_row.get("explanation"),
            target_piece=tactic_row.get("target_piece"),
            target_square=tactic_row.get("target_square"),
            eval_cp=tactic_row.get("eval_cp", 0),
        )

    @staticmethod
    def build_outcome_insert_plan(
        outcome_row: Mapping[str, object],
    ) -> OutcomeInsertPlan:
        """Build an outcome insert plan from a row mapping."""
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
        query: DashboardQuery | str | None = None,
        *,
        filters: DashboardQuery | None = None,
        **legacy: object,
    ) -> dict[str, object]:
        """Build a dashboard payload for the store implementation."""

        raise NotImplementedError("Subclasses must implement get_dashboard_payload")
