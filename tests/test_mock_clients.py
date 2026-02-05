from datetime import datetime, timezone
from pathlib import Path

from tactix.chess_clients.base_chess_client import (
    BaseChessClientContext,
    ChessFetchRequest,
)
from tactix.define_base_db_store_context__db_store import BaseDbStoreContext
from tactix.chess_clients.chess_game_row import ChessGameRow
from tactix.config import Settings
from tactix.utils.logger import Logger
from tactix.chess_clients.mock_chess_client import MockChessClient
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


def test_mock_chess_client_applies_window_filter() -> None:
    settings = _settings()
    context = BaseChessClientContext(settings=settings, logger=get_logger("test"))
    games = [
        {
            "game_id": "g1",
            "user": "tester",
            "source": "lichess",
            "fetched_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "pgn": "[Event]\n\n1. e4 *",
            "last_timestamp_ms": 50,
        },
        {
            "game_id": "g2",
            "user": "tester",
            "source": "lichess",
            "fetched_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "pgn": "[Event]\n\n1. d4 *",
            "last_timestamp_ms": 150,
        },
        {
            "game_id": "g3",
            "user": "tester",
            "source": "lichess",
            "fetched_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "pgn": "[Event]\n\n1. c4 *",
            "last_timestamp_ms": 250,
        },
    ]
    client = MockChessClient(context, games=games)

    result = client.fetch_incremental_games(ChessFetchRequest(since_ms=100, until_ms=200))

    assert [row["game_id"] for row in result.games] == ["g2"]
    assert result.last_timestamp_ms == 150


def test_mock_chess_client_paginates_with_cursor() -> None:
    settings = _settings()
    context = BaseChessClientContext(settings=settings, logger=get_logger("test"))
    games = [
        {
            "game_id": "g1",
            "user": "tester",
            "source": "lichess",
            "fetched_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "pgn": "[Event]\n\n1. e4 *",
            "last_timestamp_ms": 10,
        },
        {
            "game_id": "g2",
            "user": "tester",
            "source": "lichess",
            "fetched_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "pgn": "[Event]\n\n1. d4 *",
            "last_timestamp_ms": 20,
        },
        {
            "game_id": "g3",
            "user": "tester",
            "source": "lichess",
            "fetched_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "pgn": "[Event]\n\n1. c4 *",
            "last_timestamp_ms": 30,
        },
    ]
    client = MockChessClient(context, games=games, page_size=1)

    first = client.fetch_incremental_games(ChessFetchRequest())
    assert [row["game_id"] for row in first.games] == ["g1"]
    assert first.next_cursor == "1"

    second = client.fetch_incremental_games(ChessFetchRequest(cursor="1"))
    assert [row["game_id"] for row in second.games] == ["g2"]
    assert second.next_cursor == "2"


def test_mock_chess_client_handles_invalid_cursor() -> None:
    settings = _settings()
    context = BaseChessClientContext(settings=settings, logger=get_logger("test"))
    games = [
        {
            "game_id": "g1",
            "user": "tester",
            "source": "lichess",
            "fetched_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "pgn": "[Event]\n\n1. e4 *",
            "last_timestamp_ms": 10,
        },
        {
            "game_id": "g2",
            "user": "tester",
            "source": "lichess",
            "fetched_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "pgn": "[Event]\n\n1. d4 *",
            "last_timestamp_ms": 20,
        },
    ]
    client = MockChessClient(context, games=games, page_size=1)

    result = client.fetch_incremental_games(ChessFetchRequest(cursor="not-a-number"))

    assert [row["game_id"] for row in result.games] == ["g1"]
    assert result.next_cursor == "1"


def test_mock_chess_client_respects_full_history() -> None:
    settings = _settings()
    context = BaseChessClientContext(settings=settings, logger=get_logger("test"))
    games = [
        {
            "game_id": "g1",
            "user": "tester",
            "source": "lichess",
            "fetched_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "pgn": "[Event]\n\n1. e4 *",
            "last_timestamp_ms": 10,
        },
        {
            "game_id": "g2",
            "user": "tester",
            "source": "lichess",
            "fetched_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "pgn": "[Event]\n\n1. d4 *",
            "last_timestamp_ms": 200,
        },
    ]
    client = MockChessClient(context, games=games)

    result = client.fetch_incremental_games(
        ChessFetchRequest(since_ms=150, until_ms=160, full_history=True)
    )

    assert [row["game_id"] for row in result.games] == ["g1", "g2"]


def test_mock_db_store_dashboard_payload() -> None:
    settings = _settings()
    payload = {
        "source": "lichess",
        "user": "tester",
        "metrics": [{"motif": "fork"}],
        "recent_games": [{"game_id": "g1"}],
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


def test_mock_db_store_applies_filters() -> None:
    settings = _settings()
    payload = {
        "source": "lichess",
        "user": "tester",
        "metrics": [
            {
                "motif": "fork",
                "time_control": "blitz",
                "rating_bucket": "1200-1400",
                "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "source": "lichess",
            },
            {
                "motif": "pin",
                "time_control": "rapid",
                "rating_bucket": "1400-1600",
                "created_at": datetime(2024, 1, 5, tzinfo=timezone.utc),
                "source": "chesscom",
            },
        ],
        "recent_games": [
            {
                "game_id": "g1",
                "played_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "source": "lichess",
            }
        ],
        "positions": [],
        "tactics": [
            {
                "tactic_id": 1,
                "motif": "fork",
                "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "source": "lichess",
            }
        ],
        "metrics_version": 11,
    }
    store = MockDbStore(
        BaseDbStoreContext(settings=settings, logger=get_logger("test")),
        payload=payload,
    )

    result = store.get_dashboard_payload(
        source="lichess",
        motif="fork",
        rating_bucket="1200-1400",
        time_control="blitz",
        start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )

    assert result["source"] == "lichess"
    assert len(result["metrics"]) == 1
    assert len(result["tactics"]) == 1
    assert result["metrics"][0]["motif"] == "fork"


def test_mock_db_store_filters_date_ranges_and_non_dict_rows() -> None:
    settings = _settings()
    payload = {
        "source": "lichess",
        "user": "tester",
        "metrics": [
            "raw-row",
            {
                "motif": "fork",
                "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "source": "lichess",
            },
            {
                "motif": "fork",
                "created_at": datetime(2023, 12, 31, tzinfo=timezone.utc),
                "source": "lichess",
            },
        ],
        "recent_games": [],
        "positions": [],
        "tactics": [],
        "metrics_version": 12,
    }
    store = MockDbStore(
        BaseDbStoreContext(settings=settings, logger=get_logger("test")),
        payload=payload,
    )

    result = store.get_dashboard_payload(
        source="lichess",
        start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )

    assert result["metrics"][0] == "raw-row"
    assert len(result["metrics"]) == 2


def test_mock_db_store_filters_by_multiple_fields() -> None:
    settings = _settings()
    payload = {
        "source": "lichess",
        "user": "tester",
        "metrics": [
            {
                "motif": "fork",
                "time_control": "blitz",
                "rating_bucket": "1200-1400",
                "trend_date": datetime(2024, 2, 1, tzinfo=timezone.utc).date(),
                "source": "lichess",
            },
            {
                "motif": "pin",
                "time_control": "rapid",
                "rating_bucket": "1400-1600",
                "trend_date": datetime(2024, 2, 2, tzinfo=timezone.utc).date(),
                "source": "lichess",
            },
        ],
        "recent_games": [],
        "positions": [],
        "tactics": [],
        "metrics_version": 15,
    }
    store = MockDbStore(
        BaseDbStoreContext(settings=settings, logger=get_logger("test")),
        payload=payload,
    )

    result = store.get_dashboard_payload(
        source="lichess",
        motif="fork",
        rating_bucket="1200-1400",
        time_control="blitz",
        start_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
    )

    assert len(result["metrics"]) == 1
    assert result["metrics"][0]["motif"] == "fork"


def test_mock_db_store_skips_mismatched_filters_and_allows_missing_dates() -> None:
    settings = _settings()
    payload = {
        "source": "lichess",
        "user": "tester",
        "metrics": [
            {
                "motif": "fork",
                "rating_bucket": "1200-1400",
                "time_control": "blitz",
                "source": "lichess",
            },
            {
                "motif": "fork",
                "rating_bucket": "1400-1600",
                "time_control": "blitz",
                "source": "lichess",
            },
            {
                "motif": "fork",
                "rating_bucket": "1200-1400",
                "time_control": "rapid",
                "source": "lichess",
            },
        ],
        "recent_games": [],
        "positions": [],
        "tactics": [],
        "metrics_version": 16,
    }
    store = MockDbStore(
        BaseDbStoreContext(settings=settings, logger=get_logger("test")),
        payload=payload,
    )

    result = store.get_dashboard_payload(
        source="lichess",
        motif="fork",
        rating_bucket="1200-1400",
        time_control="blitz",
        start_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 2, 2, tzinfo=timezone.utc),
    )

    assert len(result["metrics"]) == 1


def test_pipeline_dashboard_uses_injected_store() -> None:
    settings = _settings()
    payload = {
        "source": "lichess",
        "user": "tester",
        "metrics": [],
        "recent_games": [],
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
