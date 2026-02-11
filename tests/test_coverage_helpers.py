import importlib
import logging
import runpy
from pathlib import Path

import chess
import chess.pgn
import pytest

import tactix.tactic_scope as tactic_scope
import tactix.utils as utils
from tactix._build_schema_label import _build_schema_label
from tactix._configure_engine_options import _configure_engine_options
from tactix._connection_kwargs import _connection_kwargs
from tactix._empty_pgn_metadata import _empty_pgn_metadata
from tactix._filter_fixture_games import _filter_fixture_games
from tactix._forks_meet_threshold import _forks_meet_threshold
from tactix._get_user_color_from_pgn_headers import _get_user_color_from_pgn_headers
from tactix._iter_position_contexts import _iter_position_contexts
from tactix._normalize_clock_parts import _normalize_clock_parts
from tactix._resolve_chesscom_profile_value import _resolve_chesscom_profile_value
from tactix._resolve_profile_value__settings import _resolve_profile_value__settings
from tactix.PgnContext import PgnContext
from tactix.TacticContext import TacticContext
from tactix.TacticDetector import TacticDetector
from tactix.define_db_schemas__const import ANALYSIS_SCHEMA, PGN_SCHEMA
from tactix.chess_player_color import ChessPlayerColor
from tactix.config import Settings
from tactix.extract_game_id import extract_game_id
from tactix.extract_last_timestamp_ms import extract_last_timestamp_ms


class DummyEngine:
    def __init__(self) -> None:
        self.configured: dict[str, object] | None = None

    def configure(self, options: dict[str, object]) -> None:
        self.configured = options


def test_build_schema_label_flags() -> None:
    settings = Settings(postgres_analysis_enabled=False, postgres_pgns_enabled=False)
    assert _build_schema_label(settings) == "tactix_ops"

    settings = Settings(postgres_analysis_enabled=True, postgres_pgns_enabled=False)
    assert _build_schema_label(settings) == f"tactix_ops,{ANALYSIS_SCHEMA}"

    settings = Settings(postgres_analysis_enabled=True, postgres_pgns_enabled=True)
    assert _build_schema_label(settings) == f"tactix_ops,{ANALYSIS_SCHEMA},{PGN_SCHEMA}"


def test_empty_pgn_metadata_defaults_to_none() -> None:
    metadata = _empty_pgn_metadata()
    assert metadata["user_rating"] is None
    assert metadata["time_control"] is None
    assert metadata["start_timestamp_ms"] is None


def test_normalize_clock_parts_handles_short_and_full() -> None:
    assert _normalize_clock_parts("01:02:03") == ("01", "02", "03")
    assert _normalize_clock_parts("02:03") == ("0", "02", "03")
    assert _normalize_clock_parts("bad") is None


def test_filter_fixture_games_respects_time_window() -> None:
    pgn_one = """
[Event "Fixture 1"]
[Site "https://lichess.org/abc123"]
[UTCDate "2024.01.01"]
[UTCTime "00:00:00"]
[White "alice"]
[Black "bob"]
[Result "1-0"]

1. e4 e5 1-0
""".strip()
    pgn_two = """
[Event "Fixture 2"]
[Site "https://lichess.org/def456"]
[UTCDate "2024.01.03"]
[UTCTime "00:00:00"]
[White "alice"]
[Black "bob"]
[Result "1-0"]

1. d4 d5 1-0
""".strip()

    first_ts = extract_last_timestamp_ms(pgn_one)
    second_ts = extract_last_timestamp_ms(pgn_two)
    since_ms = first_ts
    until_ms = second_ts + 1

    rows = _filter_fixture_games([pgn_one, pgn_two], "alice", "lichess", since_ms, until_ms)
    assert len(rows) == 1
    assert rows[0]["game_id"] == extract_game_id(pgn_two)
    assert rows[0]["last_timestamp_ms"] == second_ts


def test_reload_fixture_helpers_for_coverage() -> None:
    import tactix._build_schema_label as build_schema_label
    import tactix._empty_pgn_metadata as empty_pgn_metadata
    import tactix._filter_fixture_games as filter_fixture_games
    import tactix._normalize_clock_parts as normalize_clock_parts

    importlib.reload(build_schema_label)
    importlib.reload(empty_pgn_metadata)
    importlib.reload(filter_fixture_games)
    importlib.reload(normalize_clock_parts)

    assert str(Path(build_schema_label.__file__ or "")).endswith(
        "src/tactix/_build_schema_label.py"
    )

    settings = Settings(postgres_analysis_enabled=False, postgres_pgns_enabled=False)
    assert build_schema_label._build_schema_label(settings) == "tactix_ops"
    assert empty_pgn_metadata._empty_pgn_metadata()["user_rating"] is None
    assert normalize_clock_parts._normalize_clock_parts("00:10") == ("0", "00", "10")
    assert filter_fixture_games._filter_fixture_games([], "alice", "lichess", 0, None) == []


def test_runpy_executes_wrapper_modules() -> None:
    base_dir = Path(__file__).resolve().parents[1] / "src" / "tactix"
    rel_paths = (
        "_build_schema_label.py",
        "_disabled_raw_pgn_summary.py",
        "_empty_pgn_metadata.py",
        "_fetch_raw_pgn_summary.py",
        "_filter_fixture_games.py",
        "_insert_analysis_tactic.py",
        "_insert_raw_pgn_row.py",
        "_list_tables.py",
        "_normalize_clock_parts.py",
        "_resolve_chesscom_profile_value.py",
        "_resolve_profile_value__settings.py",
        "tactic_scope.py",
        "trigger_daily_sync__api_jobs.py",
        "utils/logger.py",
        "utils/to_int.py",
    )
    for rel_path in rel_paths:
        runpy.run_path(str(base_dir / rel_path))


def test_connection_kwargs_prefers_dsn() -> None:
    settings = Settings(postgres_dsn="postgres://example", postgres_host=None, postgres_db=None)
    assert _connection_kwargs(settings) == {"dsn": "postgres://example"}


def test_connection_kwargs_requires_host_and_db() -> None:
    settings = Settings(postgres_dsn=None, postgres_host=None, postgres_db=None)
    assert _connection_kwargs(settings) is None

    settings = Settings(
        postgres_dsn=None,
        postgres_host="localhost",
        postgres_db="tactix",
        postgres_user="user",
        postgres_password="pass",
        postgres_port=5432,
        postgres_sslmode="disable",
        postgres_connect_timeout_s=5,
    )
    assert _connection_kwargs(settings) == {
        "host": "localhost",
        "port": 5432,
        "dbname": "tactix",
        "user": "user",
        "password": "pass",
        "sslmode": "disable",
        "connect_timeout": 5,
    }


def test_forks_meet_threshold_respects_check_state() -> None:
    check_board = chess.Board("7k/7Q/7K/8/8/8/8/8 b - - 0 1")
    assert check_board.is_check()
    assert _forks_meet_threshold(1, check_board)
    assert not _forks_meet_threshold(0, check_board)

    safe_board = chess.Board()
    assert not safe_board.is_check()
    assert _forks_meet_threshold(2, safe_board)
    assert not _forks_meet_threshold(1, safe_board)


def test_get_user_color_from_pgn_headers() -> None:
    headers = chess.pgn.Headers()
    headers["White"] = "Alice"
    headers["Black"] = "Bob"

    assert _get_user_color_from_pgn_headers(headers, "Alice") == ChessPlayerColor.WHITE
    assert _get_user_color_from_pgn_headers(headers, "Bob") == ChessPlayerColor.BLACK

    with pytest.raises(ValueError):
        _get_user_color_from_pgn_headers(headers, "Carol")


def test_configure_engine_options_sets_options() -> None:
    engine = DummyEngine()
    options = {"Threads": 1}
    assert _configure_engine_options(engine, options) == options
    assert engine.configured == options


def test_utils_exports_are_available() -> None:
    importlib.reload(utils)
    for name in utils.__all__:
        assert hasattr(utils, name)
    assert utils.normalize_string(" Test ") == "test"
    assert utils.hash("abc")


def test_tactic_scope_filters() -> None:
    importlib.reload(tactic_scope)
    assert tactic_scope.is_allowed_motif_filter(None)
    assert tactic_scope.is_allowed_motif_filter("hanging_piece")
    assert not tactic_scope.is_allowed_motif_filter("fork")
    assert tactic_scope.allowed_motif_list() == tactic_scope.ALLOWED_MOTIFS
    assert not tactic_scope.is_supported_motif(None)


def test_to_int_parses_variants() -> None:
    from tactix.utils.to_int import to_int

    assert to_int(3) == 3
    assert to_int("4") == 4
    assert to_int("bad") is None
    assert to_int(3.2) is None


def test_logger_helpers_apply_levels() -> None:
    from tactix.utils.logger import get_logger, set_level

    logger = get_logger("coverage-test")
    set_level(logging.INFO, ["coverage-test"])
    assert logger.level == logging.INFO


def test_profile_value_resolvers() -> None:
    settings = Settings(source="chesscom", chesscom_profile="daily")
    assert _resolve_chesscom_profile_value(settings) == "correspondence"
    assert _resolve_profile_value__settings(settings) == "correspondence"

    lichess_settings = Settings(source="lichess", lichess_profile="blitz")
    assert _resolve_profile_value__settings(lichess_settings) == "blitz"


def test_wrapper_modules_expose_symbols() -> None:
    import tactix._disabled_raw_pgn_summary as disabled_summary
    import tactix._fetch_raw_pgn_summary as fetch_summary
    import tactix._insert_analysis_tactic as insert_tactic
    import tactix._insert_raw_pgn_row as insert_raw_pgn_row

    importlib.reload(disabled_summary)
    importlib.reload(fetch_summary)
    importlib.reload(insert_tactic)
    importlib.reload(insert_raw_pgn_row)

    assert hasattr(disabled_summary, "_disabled_raw_pgn_summary")
    assert hasattr(fetch_summary, "_fetch_raw_pgn_summary")
    assert hasattr(insert_tactic, "_insert_analysis_tactic")
    assert hasattr(insert_raw_pgn_row, "_insert_raw_pgn_row")


def test_tactic_context_fields() -> None:
    board_before = chess.Board()
    move = chess.Move.from_uci("e2e4")
    board_after = board_before.copy()
    board_after.push(move)

    context = TacticContext(
        board_before=board_before,
        board_after=board_after,
        best_move=move,
        mover_color=chess.WHITE,
    )
    assert context.board_before == board_before
    assert context.board_after == board_after
    assert context.best_move == move
    assert context.mover_color == chess.WHITE


def test_tactic_detector_protocol_runtime_check() -> None:
    class DummyDetector:
        motif = "dummy"

        def detect(self, _context: TacticContext) -> list[object]:
            return []

    assert isinstance(DummyDetector(), TacticDetector)


def test_iter_position_contexts_builds_positions() -> None:
    pgn = """
[Event "Test"]
[Site "https://lichess.org/pos123"]
[UTCDate "2024.01.01"]
[UTCTime "00:00:00"]
[White "alice"]
[Black "bob"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 1-0
""".strip()
    ctx = PgnContext(pgn, user="alice", source="lichess")
    game = ctx.game
    assert game is not None
    board = game.board()

    positions = _iter_position_contexts(ctx, game, board, chess.WHITE, None)
    assert len(positions) == 2
    assert positions[0]["uci"] == "e2e4"
