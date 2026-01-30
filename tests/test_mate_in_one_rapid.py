import shutil
import tempfile
import unittest
from pathlib import Path

import chess

from tactix.config import DEFAULT_RAPID_STOCKFISH_DEPTH, Settings
from tactix.duckdb_store import (
    get_connection,
    grade_practice_attempt,
    init_schema,
    insert_positions,
    upsert_tactic_with_outcome,
)
from tactix.pgn_utils import split_pgn_chunks
from tactix.position_extractor import extract_positions
from tactix.stockfish_runner import StockfishEngine
from tactix.tactics_analyzer import analyze_position


def _find_missed_position(
    position: dict[str, object],
    engine: StockfishEngine,
    settings: Settings,
    expected_motif: str,
) -> tuple[dict[str, object], tuple[dict[str, object], dict[str, object]]]:
    board = chess.Board(str(position["fen"]))
    best_move = engine.analyse(board).best_move
    for move in board.legal_moves:
        if best_move is not None and move == best_move:
            continue
        candidate = dict(position)
        candidate["uci"] = move.uci()
        try:
            candidate["san"] = board.san(move)
        except Exception:
            pass
        result = analyze_position(candidate, engine, settings=settings)
        if result is None:
            continue
        tactic_row, outcome_row = result
        if outcome_row["result"] == "missed" and tactic_row["motif"] == expected_motif:
            return candidate, result
    raise AssertionError("No missed outcome found for fixture position")


def _find_failed_attempt_position(
    position: dict[str, object],
    engine: StockfishEngine,
    settings: Settings,
    expected_motif: str,
) -> tuple[dict[str, object], tuple[dict[str, object], dict[str, object]]]:
    board = chess.Board(str(position["fen"]))
    best_move = engine.analyse(board).best_move
    for move in board.legal_moves:
        if best_move is not None and move == best_move:
            continue
        candidate = dict(position)
        candidate["uci"] = move.uci()
        try:
            candidate["san"] = board.san(move)
        except Exception:
            pass
        result = analyze_position(candidate, engine, settings=settings)
        if result is None:
            continue
        tactic_row, outcome_row = result
        if (
            outcome_row["result"] == "failed_attempt"
            and tactic_row["motif"] == expected_motif
        ):
            return candidate, result
    raise AssertionError("No failed_attempt outcome found for fixture position")


class MateInOneRapidTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_rapid_mate_in_one_is_high_severity(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "chesscom_rapid_sample.pgn"
        )
        chunks = split_pgn_chunks(fixture_path.read_text())
        mate_pgn = next(chunk for chunk in chunks if "Rapid Fixture 3" in chunk)

        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="rapid",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("rapid")
        self.assertEqual(settings.stockfish_depth, DEFAULT_RAPID_STOCKFISH_DEPTH)

        positions = extract_positions(
            mate_pgn,
            settings.chesscom_user,
            settings.source,
            game_id="rapid-mate-1",
            side_to_move_filter="black",
        )
        mate_position = next(pos for pos in positions if pos["uci"] == "d8h4")

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "mate_in_one_rapid.duckdb")
        init_schema(conn)
        position_ids = insert_positions(conn, [mate_position])
        mate_position["position_id"] = position_ids[0]

        with StockfishEngine(settings) as engine:
            result = analyze_position(mate_position, engine, settings=settings)

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "mate")
        self.assertEqual(tactic_row["best_uci"], "d8h4")
        self.assertGreaterEqual(tactic_row["severity"], 1.5)
        self.assertLessEqual(abs(outcome_row["eval_delta"]), 100)
        self.assertEqual(outcome_row["result"], "found")

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored_position_id = conn.execute(
            "SELECT position_id FROM tactics WHERE tactic_id = ?", [tactic_id]
        ).fetchone()[0]
        self.assertEqual(stored_position_id, position_ids[0])
        stored_outcome = conn.execute(
            "SELECT result, user_uci FROM tactic_outcomes WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored_outcome[0], "found")
        self.assertEqual(stored_outcome[1], "d8h4")

        attempt = grade_practice_attempt(conn, tactic_id, position_ids[0], "d8h4")
        self.assertIn("Best line", attempt["explanation"] or "")
        self.assertIn("h4", attempt["explanation"] or "")

    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_rapid_mate_in_one_records_missed_outcome(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "chesscom_rapid_sample.pgn"
        )
        chunks = split_pgn_chunks(fixture_path.read_text())
        mate_pgn = next(chunk for chunk in chunks if "Rapid Fixture 3" in chunk)

        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="rapid",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("rapid")

        positions = extract_positions(
            mate_pgn,
            settings.chesscom_user,
            settings.source,
            game_id="rapid-mate-1",
            side_to_move_filter="black",
        )
        mate_position = next(pos for pos in positions if pos["uci"] == "d8h4")

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "mate_in_one_rapid_missed.duckdb")
        init_schema(conn)

        with StockfishEngine(settings) as engine:
            missed_position, result = _find_missed_position(
                mate_position, engine, settings, "mate"
            )

        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "mate")
        self.assertEqual(outcome_row["result"], "missed")

        position_ids = insert_positions(conn, [missed_position])
        tactic_row["position_id"] = position_ids[0]

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored_outcome = conn.execute(
            "SELECT result, user_uci FROM tactic_outcomes WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored_outcome[0], "missed")
        self.assertEqual(stored_outcome[1], missed_position["uci"])

    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_rapid_mate_in_one_records_failed_attempt_outcome(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "chesscom_rapid_sample.pgn"
        )
        chunks = split_pgn_chunks(fixture_path.read_text())
        mate_pgn = next(chunk for chunk in chunks if "Rapid Fixture 3" in chunk)

        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="rapid",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("rapid")

        positions = extract_positions(
            mate_pgn,
            settings.chesscom_user,
            settings.source,
            game_id="rapid-mate-1",
            side_to_move_filter="black",
        )
        mate_position = next(pos for pos in positions if pos["uci"] == "d8h4")

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "mate_in_one_rapid_failed_attempt.duckdb")
        init_schema(conn)

        with StockfishEngine(settings) as engine:
            failed_position, result = _find_failed_attempt_position(
                mate_position, engine, settings, "mate"
            )

        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "mate")
        self.assertEqual(outcome_row["result"], "failed_attempt")

        position_ids = insert_positions(conn, [failed_position])
        tactic_row["position_id"] = position_ids[0]

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored_outcome = conn.execute(
            "SELECT result, user_uci FROM tactic_outcomes WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored_outcome[0], "failed_attempt")
        self.assertEqual(stored_outcome[1], failed_position["uci"])


class TestForkRapid(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_rapid_fork_is_low_severity(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "chesscom_rapid_sample.pgn"
        )
        chunks = split_pgn_chunks(fixture_path.read_text())
        fork_pgn = next(chunk for chunk in chunks if "Rapid Fixture 5" in chunk)

        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="rapid",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("rapid")
        self.assertEqual(settings.stockfish_depth, DEFAULT_RAPID_STOCKFISH_DEPTH)

        positions = extract_positions(
            fork_pgn,
            settings.chesscom_user,
            settings.source,
            game_id="rapid-fork",
            side_to_move_filter="black",
        )
        fork_position = next(pos for pos in positions if pos["uci"] == "f4e2")

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "fork_rapid.duckdb")
        init_schema(conn)
        position_ids = insert_positions(conn, [fork_position])
        fork_position["position_id"] = position_ids[0]

        with StockfishEngine(settings) as engine:
            result = analyze_position(fork_position, engine, settings=settings)

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "fork")
        self.assertEqual(tactic_row["best_uci"], "f4e2")
        self.assertGreater(tactic_row["severity"], 0)
        self.assertLessEqual(tactic_row["severity"], 1.0)
        self.assertEqual(outcome_row["result"], "found")

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored = conn.execute(
            "SELECT position_id, best_san, explanation FROM tactics WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored[0], position_ids[0])
        self.assertIsNotNone(stored[1])
        self.assertIn("Best line", stored[2] or "")
        stored_outcome = conn.execute(
            "SELECT result, user_uci FROM tactic_outcomes WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored_outcome[0], "found")
        self.assertEqual(stored_outcome[1], "f4e2")

        attempt = grade_practice_attempt(conn, tactic_id, position_ids[0], "f4e2")
        self.assertIn("Best line", attempt["explanation"] or "")
        self.assertIn("e2", attempt["explanation"] or "")

    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_rapid_fork_records_missed_outcome(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "chesscom_rapid_sample.pgn"
        )
        chunks = split_pgn_chunks(fixture_path.read_text())
        fork_pgn = next(chunk for chunk in chunks if "Rapid Fixture 5" in chunk)

        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="rapid",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("rapid")

        positions = extract_positions(
            fork_pgn,
            settings.chesscom_user,
            settings.source,
            game_id="rapid-fork",
            side_to_move_filter="black",
        )
        fork_position = next(pos for pos in positions if pos["uci"] == "f4e2")

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "fork_rapid_missed.duckdb")
        init_schema(conn)

        with StockfishEngine(settings) as engine:
            missed_position, result = _find_missed_position(
                fork_position, engine, settings, "fork"
            )

        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "fork")
        self.assertEqual(outcome_row["result"], "missed")

        position_ids = insert_positions(conn, [missed_position])
        tactic_row["position_id"] = position_ids[0]

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored_outcome = conn.execute(
            "SELECT result, user_uci FROM tactic_outcomes WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored_outcome[0], "missed")
        self.assertEqual(stored_outcome[1], missed_position["uci"])

    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_rapid_fork_records_failed_attempt_outcome(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "chesscom_rapid_sample.pgn"
        )
        chunks = split_pgn_chunks(fixture_path.read_text())
        fork_pgn = next(chunk for chunk in chunks if "Rapid Fixture 5" in chunk)

        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="rapid",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("rapid")

        positions = extract_positions(
            fork_pgn,
            settings.chesscom_user,
            settings.source,
            game_id="rapid-fork",
            side_to_move_filter="black",
        )
        fork_position = next(pos for pos in positions if pos["uci"] == "f4e2")

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "fork_rapid_failed_attempt.duckdb")
        init_schema(conn)

        with StockfishEngine(settings) as engine:
            failed_position, result = _find_failed_attempt_position(
                fork_position, engine, settings, "fork"
            )

        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "fork")
        self.assertEqual(outcome_row["result"], "failed_attempt")

        position_ids = insert_positions(conn, [failed_position])
        tactic_row["position_id"] = position_ids[0]

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored_outcome = conn.execute(
            "SELECT result, user_uci FROM tactic_outcomes WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored_outcome[0], "failed_attempt")
        self.assertEqual(stored_outcome[1], failed_position["uci"])


if __name__ == "__main__":
    unittest.main()
