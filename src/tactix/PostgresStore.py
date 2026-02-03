from typing import Any

from tactix.base_db_store import BaseDbStore, BaseDbStoreContext
from tactix.PostgresStatus import PostgresStatus


class PostgresStore(BaseDbStore):
    """Postgres-backed store implementation."""

    def __init__(self, context: BaseDbStoreContext) -> None:
        super().__init__(context)

    def get_status(self) -> PostgresStatus:
        from tactix import postgres_store  # noqa: PLC0415

        return postgres_store.get_postgres_status(self.settings)

    def fetch_ops_events(self, limit: int = 10) -> list[dict[str, Any]]:
        from tactix import postgres_store  # noqa: PLC0415

        return postgres_store.fetch_ops_events(self.settings, limit=limit)

    def fetch_analysis_tactics(self, limit: int = 10) -> list[dict[str, Any]]:
        from tactix import postgres_store  # noqa: PLC0415

        return postgres_store.fetch_analysis_tactics(self.settings, limit=limit)

    def fetch_raw_pgns_summary(self) -> dict[str, Any]:
        from tactix import postgres_store  # noqa: PLC0415

        return postgres_store.fetch_postgres_raw_pgns_summary(self.settings)
