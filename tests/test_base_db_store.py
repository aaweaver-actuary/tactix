import hashlib
from datetime import timezone

import pytest

from tactix.base_db_store import BaseDbStore, BaseDbStoreContext
from tactix.config import Settings
from tactix.utils.logger import Logger
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
    assert BaseDbStore.hash_pgn("pgn") == expected


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


def test_build_pgn_upsert_plan_skips_matching_hash() -> None:
    pgn_text = "pgn"
    latest_hash = BaseDbStore.hash_pgn(pgn_text)
    plan = BaseDbStore.build_pgn_upsert_plan(
        pgn_text=pgn_text,
        user="alice",
        latest_hash=latest_hash,
        latest_version=1,
    )
    assert plan is None


def test_build_pgn_upsert_plan_includes_metadata_and_version() -> None:
    def _normalize(value: str) -> str:
        return f"{value}-normalized"

    plan = BaseDbStore.build_pgn_upsert_plan(
        pgn_text=PGN_SAMPLE,
        user="alice",
        latest_hash="other",
        latest_version=2,
        normalize_pgn=_normalize,
    )

    assert plan is not None
    assert plan.pgn_version == 3
    assert plan.normalized_pgn == f"{PGN_SAMPLE}-normalized"
    assert plan.metadata.get("time_control") == "300+0"


def test_require_position_id_raises_when_missing() -> None:
    with pytest.raises(ValueError):
        BaseDbStore.require_position_id({}, "position_id required")


def test_build_tactic_insert_plan_applies_defaults() -> None:
    plan = BaseDbStore.build_tactic_insert_plan(
        game_id="game-1",
        position_id=12,
        tactic_row={},
    )

    assert plan.game_id == "game-1"
    assert plan.position_id == 12
    assert plan.motif == "unknown"
    assert plan.severity == 0.0
    assert plan.best_uci == ""
    assert plan.eval_cp == 0


def test_build_outcome_insert_plan_applies_defaults() -> None:
    plan = BaseDbStore.build_outcome_insert_plan({})

    assert plan.result == "unclear"
    assert plan.user_uci == ""
    assert plan.eval_delta == 0


def test_base_db_store_exposes_logger() -> None:
    store = MockDbStore(_context())
    assert store.logger.name == "test"
