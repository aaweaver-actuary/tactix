from __future__ import annotations

from datetime import datetime

from tactix.base_db_store import BaseDbStore, BaseDbStoreContext


class MockDbStore(BaseDbStore):
    """Mock database store that serves in-memory dashboard payloads."""

    def __init__(
        self, context: BaseDbStoreContext, payload: dict[str, object] | None = None
    ) -> None:
        super().__init__(context)
        self._payload = payload or {
            "source": context.settings.source,
            "user": context.settings.user,
            "metrics": [],
            "recent_games": [],
            "positions": [],
            "tactics": [],
            "metrics_version": 0,
        }

    def get_dashboard_payload(
        self,
        source: str | None = None,
        motif: str | None = None,
        rating_bucket: str | None = None,
        time_control: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, object]:
        payload = dict(self._payload)
        normalized_source = None if source in (None, "all") else source
        payload["source"] = normalized_source or "all"
        payload["user"] = self.settings.user
        return payload
