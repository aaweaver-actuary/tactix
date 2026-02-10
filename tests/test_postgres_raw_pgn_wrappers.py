from unittest.mock import MagicMock, patch

import tactix.fetch_postgres_raw_pgns_summary as summary_wrapper
from tactix.db.postgres_raw_pgn_repository import fetch_postgres_raw_pgns_summary
from tactix.upsert_postgres_raw_pgns import upsert_postgres_raw_pgns


def test_fetch_postgres_raw_pgns_summary_is_reexported() -> None:
    assert summary_wrapper.fetch_postgres_raw_pgns_summary is fetch_postgres_raw_pgns_summary


def test_upsert_postgres_raw_pgns_delegates_to_repository() -> None:
    repo = MagicMock()
    repo.upsert_raw_pgns.return_value = 3
    with patch(
        "tactix.upsert_postgres_raw_pgns.PostgresRawPgnRepository",
        return_value=repo,
    ) as repo_factory:
        conn = object()
        rows = [{"game_id": "chesscom-1", "pgn": "1. e4 e5"}]

        result = upsert_postgres_raw_pgns(conn, rows)

    repo_factory.assert_called_once_with(conn)
    repo.upsert_raw_pgns.assert_called_once_with(rows)
    assert result == 3
