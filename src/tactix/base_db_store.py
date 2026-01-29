from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import logging
from typing import Mapping

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
