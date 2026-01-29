from datetime import datetime, timezone
from pathlib import Path

from tactix.base_chess_client import BaseChessClientContext, ChessFetchRequest, ChessGameRow
from tactix.base_db_store import BaseDbStoreContext
from tactix.config import Settings
from tactix.logging_utils import get_logger
from tactix.mock_chess_client import MockChessClient
from tactix.mock_db_store import MockDbStore
from tactix.pipeline import get_dashboard_payload


def _settings() -> Settings:
    return Settings(
        user="tester",
        source="lichess",
        duckdb_path=Path("/tmp/mock.duckdb"),
        checkpoint_path=Path("/tmp/since.txt"),
        metrics_version_file=Path("/tmp/metrics.txt"),
    )


def test_mock_chess_client_returns_in_memory_games() -> None:
    settings = _settings()
    context = BaseChessClientContext(settings=settings, logger=get_logger("test"))
    games = [
        ChessGameRow(
            game_id="game-1",
            user="tester",
            source="lichess",
            fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            pgn="[Event]\n\n1. e4 *",
            last_timestamp_ms=123,
        )
    ]
    client = MockChessClient(context, games=games, next_cursor="cursor-1")

    result = client.fetch_incremental_games(ChessFetchRequest())

    assert result.games[0]["game_id"] == "game-1"
    assert result.next_cursor == "cursor-1"
    assert result.last_timestamp_ms == 123


def test_mock_db_store_dashboard_payload() -> None:
    settings = _settings()
    payload = {
        "source": "lichess",
        "user": "tester",
        "metrics": [{"motif": "fork"}],
        "positions": [{"position_id": 1}],
        "tactics": [{"tactic_id": 2}],
        "metrics_version": 7,
    }
    store = MockDbStore(
        BaseDbStoreContext(settings=settings, logger=get_logger("test")),
        payload=payload,
    )

    result = store.get_dashboard_payload(source="chesscom")

    assert result["source"] == "chesscom"
    assert result["user"] == "tester"
    assert result["metrics_version"] == 7


def test_pipeline_dashboard_uses_injected_store() -> None:
    settings = _settings()
    payload = {
        "source": "lichess",
        "user": "tester",
        "metrics": [],
        "positions": [],
        "tactics": [],
        "metrics_version": 3,
    }
    store = MockDbStore(
        BaseDbStoreContext(settings=settings, logger=get_logger("test")),
        payload=payload,
    )

    result = get_dashboard_payload(settings=settings, store=store)

    assert result["metrics_version"] == 3
    assert result["source"] == "all"
