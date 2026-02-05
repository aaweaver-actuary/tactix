import tempfile
import unittest
from pathlib import Path

from tactix.dashboard_query import DashboardQuery
from tactix.db.dashboard_repository_provider import (
    dashboard_repository,
    fetch_metrics,
    fetch_motif_stats,
    fetch_pipeline_table_counts,
    fetch_recent_tactics,
    fetch_trend_stats,
)
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.metrics_repository_provider import update_metrics_summary


class DashboardRepositoryProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.conn = get_connection(self.tmp_dir / "dashboard.duckdb")
        init_schema(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_dashboard_repository_provider_returns_repository(self) -> None:
        repo = dashboard_repository(self.conn)
        self.assertIsNotNone(repo)

    def test_dashboard_repository_provider_fetches_empty_rows(self) -> None:
        update_metrics_summary(self.conn)
        query = DashboardQuery(source="all")

        self.assertEqual(fetch_metrics(self.conn, query), [])
        self.assertEqual(fetch_motif_stats(self.conn, query), [])
        self.assertEqual(fetch_trend_stats(self.conn, query), [])
        self.assertEqual(fetch_recent_tactics(self.conn, query, limit=5), [])
        self.assertEqual(fetch_pipeline_table_counts(self.conn, query)["games"], 0)


if __name__ == "__main__":
    unittest.main()
