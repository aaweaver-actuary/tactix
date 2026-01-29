import hashlib
from datetime import timezone

import pytest

from tactix.base_db_store import BaseDbStore, BaseDbStoreContext
from tactix.config import Settings
from tactix.logging_utils import get_logger
from tactix.mock_db_store import MockDbStore
from tactix.pgn_utils import extract_pgn_metadata


PGN_SAMPLE = """[Event "Test"]
[Site "https://lichess.org/AbcDef12"]
[UTCDate "2020.01.02"]
[UTCTime "03:04:05"]
[White "alice"]
[Black "bob"]
[WhiteElo "1500"]
[BlackElo "1600"]
[TimeControl "300+0"]
[Result "*"]

1. e4 *
"""


def _context() -> BaseDbStoreContext:
    settings = Settings(
        user="tester",
        source="lichess",
        duckdb_path="/tmp/db.duckdb",
        checkpoint_path="/tmp/since.txt",
        metrics_version_file="/tmp/metrics.txt",
    )
    return BaseDbStoreContext(settings=settings, logger=get_logger("test"))


def test_hash_pgn_text_matches_sha256() -> None:
    expected = hashlib.sha256("pgn".encode("utf-8")).hexdigest()
    assert BaseDbStore.hash_pgn_text("pgn") == expected


def test_extract_pgn_metadata_matches_helper() -> None:
    expected = extract_pgn_metadata(PGN_SAMPLE, "alice")
    actual = BaseDbStore.extract_pgn_metadata(PGN_SAMPLE, "alice")
    assert actual.get("time_control") == expected.get("time_control")


def test_now_utc_is_timezone_aware() -> None:
    store = MockDbStore(_context())
    now = store._now_utc()
    assert now.tzinfo == timezone.utc


def test_base_store_requires_dashboard_payload() -> None:
    store = BaseDbStore(_context())
    with pytest.raises(NotImplementedError):
        store.get_dashboard_payload()
