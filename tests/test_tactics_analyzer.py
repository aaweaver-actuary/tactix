import tempfile
import unittest
from pathlib import Path

import chess

from tactix.config import Settings
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.position_repository_provider import insert_positions
from tactix.db.tactic_repository_provider import upsert_tactic_with_outcome
from tactix.engine_result import EngineResult
from tactix.detect_tactics__motifs import BaseTacticDetector, build_default_motif_detector_suite
from tactix._is_profile_in import _is_profile_in
from tactix.analyze_position import analyze_position
from tests.fixture_helpers import (
    discovered_attack_fixture_position,
    hanging_piece_fixture_position,
    pin_fixture_position,
    skewer_fixture_position,
)


class TacticsAnalyzerTests(unittest.TestCase):
    def test_classify_result_variants(self) -> None:
        self.assertEqual(
            BaseTacticDetector.classify_result("e2e4", "e2e4", 0, 120),
            ("found", 120),
        )
        self.assertEqual(
            BaseTacticDetector.classify_result("e2e4", "d2d4", 100, -250),
            ("missed", -350),
        )
        self.assertEqual(
            BaseTacticDetector.classify_result(None, "d2d4", -50, -200),
            ("failed_attempt", -150),
        )
        self.assertEqual(
            BaseTacticDetector.classify_result("e2e4", "d2d4", 20, -30),
            ("unclear", -50),
        )

    def test_score_from_pov(self) -> None:
        self.assertEqual(BaseTacticDetector.score_from_pov(120, chess.WHITE, chess.WHITE), 120)
        self.assertEqual(BaseTacticDetector.score_from_pov(120, chess.WHITE, chess.BLACK), -120)
        self.assertEqual(BaseTacticDetector.score_from_pov(-80, chess.BLACK, chess.WHITE), 80)

    def test_infer_motif_fork_detection(self) -> None:
        suite = build_default_motif_detector_suite()
        board = chess.Board(None)
        board.clear()
        board.set_piece_at(chess.F5, chess.Piece(chess.KNIGHT, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.QUEEN, chess.BLACK))
        board.set_piece_at(chess.F7, chess.Piece(chess.ROOK, chess.BLACK))
        board.set_piece_at(chess.A1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.H8, chess.Piece(chess.KING, chess.BLACK))
        board.turn = chess.WHITE

        motif = suite.infer_motif(board, chess.Move.from_uci("f5d6"))
        self.assertEqual(motif, "fork")

    def test_infer_motif_hanging_capture(self) -> None:
        suite = build_default_motif_detector_suite()
        board = chess.Board(None)
        board.clear()
        board.set_piece_at(chess.C4, chess.Piece(chess.BISHOP, chess.WHITE))
        board.set_piece_at(chess.E6, chess.Piece(chess.ROOK, chess.BLACK))
        board.set_piece_at(chess.A1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.H8, chess.Piece(chess.KING, chess.BLACK))
        board.turn = chess.WHITE

        motif = suite.infer_motif(board, chess.Move.from_uci("c4e6"))
        self.assertEqual(motif, "hanging_piece")

    def test_hanging_capture_when_trade_wins_material(self) -> None:
        board = chess.Board(None)
        board.clear()
        board.set_piece_at(chess.D5, chess.Piece(chess.PAWN, chess.WHITE))
        board.set_piece_at(chess.C6, chess.Piece(chess.KNIGHT, chess.BLACK))
        board.set_piece_at(chess.B7, chess.Piece(chess.PAWN, chess.BLACK))
        board.set_piece_at(chess.A1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.H8, chess.Piece(chess.KING, chess.BLACK))
        board.turn = chess.WHITE

        move = chess.Move.from_uci("d5c6")
        board_after = board.copy()
        board_after.push(move)

        self.assertTrue(
            BaseTacticDetector.is_hanging_capture(board, board_after, move, mover_color=chess.WHITE)
        )

    def test_hanging_piece_exposure_after_quiet_move(self) -> None:
        board = chess.Board(None)
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.D5, chess.Piece(chess.PAWN, chess.WHITE))
        board.set_piece_at(chess.C6, chess.Piece(chess.KNIGHT, chess.BLACK))
        board.set_piece_at(chess.E5, chess.Piece(chess.PAWN, chess.BLACK))
        board.turn = chess.BLACK

        move = chess.Move.from_uci("e5e4")
        board_after = board.copy()
        board_after.push(move)

        self.assertTrue(BaseTacticDetector.has_hanging_piece(board_after, chess.BLACK))

    def test_is_profile_in_handles_chesscom_daily(self) -> None:
        chesscom_daily = Settings(source="chesscom", chesscom_profile="daily")
        self.assertTrue(_is_profile_in(chesscom_daily, {"correspondence"}))
        self.assertFalse(_is_profile_in(chesscom_daily, {"bullet", "blitz"}))

    def test_is_profile_in_normalizes_profiles(self) -> None:
        lichess_rapid = Settings(source="lichess", lichess_profile="Rapid")
        self.assertTrue(_is_profile_in(lichess_rapid, {"rapid"}))
        self.assertFalse(_is_profile_in(lichess_rapid, {"blitz"}))

    def test_mate_in_two_unclear_persists(self) -> None:
        class StubEngine:
            def __init__(self) -> None:
                self.calls = 0

            def analyse(self, board: chess.Board) -> EngineResult:
                self.calls += 1
                score_cp = 100000 if board.turn == chess.WHITE else -100000
                return EngineResult(
                    best_move=chess.Move.from_uci("e2e4"),
                    score_cp=score_cp,
                    depth=12,
                    mate_in=2,
                )

        board = chess.Board()
        user_move = chess.Move.from_uci("d2d4")
        position = {
            "game_id": "unit-mate-in-two",
            "user": "unit",
            "source": "lichess",
            "fen": board.fen(),
            "ply": board.ply(),
            "move_number": board.fullmove_number,
            "side_to_move": "white",
            "uci": user_move.uci(),
            "san": board.san(user_move),
            "clock_seconds": None,
            "is_legal": True,
        }

        result = analyze_position(position, StubEngine())

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "mate")
        self.assertEqual(outcome_row["result"], "unclear")

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "mate_in_two_unclear.duckdb")
        init_schema(conn)
        position_ids = insert_positions(conn, [position])
        tactic_row["position_id"] = position_ids[0]

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored_outcome = conn.execute(
            "SELECT result, user_uci FROM tactic_outcomes WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored_outcome[0], "unclear")
        self.assertEqual(stored_outcome[1], position["uci"])

    def test_mate_in_one_unclear_persists(self) -> None:
        class StubEngine:
            def __init__(self) -> None:
                self.calls = 0

            def analyse(self, board: chess.Board) -> EngineResult:
                self.calls += 1
                score_cp = 100000 if board.turn == chess.WHITE else -100000
                return EngineResult(
                    best_move=chess.Move.from_uci("h6g7"),
                    score_cp=score_cp,
                    depth=12,
                    mate_in=1,
                )

        board = chess.Board(None)
        board.clear()
        board.set_piece_at(chess.H8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.G6, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.H6, chess.Piece(chess.QUEEN, chess.WHITE))
        board.turn = chess.WHITE
        user_move = chess.Move.from_uci("h6g5")
        position = {
            "game_id": "unit-mate-in-one",
            "user": "unit",
            "source": "lichess",
            "fen": board.fen(),
            "ply": board.ply(),
            "move_number": board.fullmove_number,
            "side_to_move": "white" if board.turn == chess.WHITE else "black",
            "uci": user_move.uci(),
            "san": board.san(user_move),
            "clock_seconds": None,
            "is_legal": True,
        }

        result = analyze_position(position, StubEngine())

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "mate")
        self.assertEqual(outcome_row["result"], "unclear")

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "mate_in_one_unclear.duckdb")
        init_schema(conn)
        position_ids = insert_positions(conn, [position])
        tactic_row["position_id"] = position_ids[0]

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored_outcome = conn.execute(
            "SELECT result, user_uci FROM tactic_outcomes WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored_outcome[0], "unclear")
        self.assertEqual(stored_outcome[1], position["uci"])

    def test_pin_unclear_persists(self) -> None:
        position = pin_fixture_position()
        board = chess.Board(str(position["fen"]))
        user_move = chess.Move.from_uci(str(position["uci"]))
        best_move = next(move for move in board.legal_moves if move != user_move)

        class StubEngine:
            def __init__(self, best: chess.Move) -> None:
                self.best_move = best

            def analyse(self, board: chess.Board) -> EngineResult:
                if not board.move_stack:
                    return EngineResult(best_move=self.best_move, score_cp=300, depth=12)
                last_move = board.move_stack[-1]
                if last_move == self.best_move:
                    return EngineResult(best_move=self.best_move, score_cp=0, depth=12)
                return EngineResult(best_move=self.best_move, score_cp=50, depth=12)

        result = analyze_position(position, StubEngine(best_move))

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "pin")
        self.assertEqual(outcome_row["result"], "unclear")

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "pin_unclear.duckdb")
        init_schema(conn)
        position_ids = insert_positions(conn, [position])
        tactic_row["position_id"] = position_ids[0]

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored_outcome = conn.execute(
            "SELECT result, user_uci FROM tactic_outcomes WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored_outcome[0], "unclear")
        self.assertEqual(stored_outcome[1], position["uci"])

    def test_skewer_unclear_persists(self) -> None:
        position = skewer_fixture_position()
        board = chess.Board(str(position["fen"]))
        user_move = chess.Move.from_uci(str(position["uci"]))
        best_move = next(move for move in board.legal_moves if move != user_move)

        class StubEngine:
            def __init__(self, best: chess.Move) -> None:
                self.best_move = best

            def analyse(self, board: chess.Board) -> EngineResult:
                if not board.move_stack:
                    return EngineResult(best_move=self.best_move, score_cp=300, depth=12)
                last_move = board.move_stack[-1]
                if last_move == self.best_move:
                    return EngineResult(best_move=self.best_move, score_cp=0, depth=12)
                return EngineResult(best_move=self.best_move, score_cp=50, depth=12)

        result = analyze_position(position, StubEngine(best_move))

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "skewer")
        self.assertEqual(outcome_row["result"], "unclear")

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "skewer_unclear.duckdb")
        init_schema(conn)
        position_ids = insert_positions(conn, [position])
        tactic_row["position_id"] = position_ids[0]

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored_outcome = conn.execute(
            "SELECT result, user_uci FROM tactic_outcomes WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored_outcome[0], "unclear")
        self.assertEqual(stored_outcome[1], position["uci"])

    def test_discovered_attack_unclear_persists(self) -> None:
        position = discovered_attack_fixture_position()
        board = chess.Board(str(position["fen"]))
        user_move = chess.Move.from_uci(str(position["uci"]))
        best_move = next(move for move in board.legal_moves if move != user_move)

        class StubEngine:
            def __init__(self, best: chess.Move) -> None:
                self.best_move = best

            def analyse(self, board: chess.Board) -> EngineResult:
                if not board.move_stack:
                    return EngineResult(best_move=self.best_move, score_cp=0, depth=12)
                last_move = board.move_stack[-1]
                if last_move == self.best_move:
                    return EngineResult(best_move=self.best_move, score_cp=0, depth=12)
                return EngineResult(best_move=self.best_move, score_cp=0, depth=12)

        result = analyze_position(position, StubEngine(best_move))

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "discovered_attack")
        self.assertEqual(outcome_row["result"], "unclear")

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "discovered_attack_unclear.duckdb")
        init_schema(conn)
        position_ids = insert_positions(conn, [position])
        tactic_row["position_id"] = position_ids[0]

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored_outcome = conn.execute(
            "SELECT result, user_uci FROM tactic_outcomes WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored_outcome[0], "unclear")
        self.assertEqual(stored_outcome[1], position["uci"])

    def test_hanging_piece_unclear_persists(self) -> None:
        position = hanging_piece_fixture_position()
        board = chess.Board(str(position["fen"]))
        user_move = chess.Move.from_uci(str(position["uci"]))
        best_move = next(move for move in board.legal_moves if move != user_move)

        class StubEngine:
            def __init__(self, best: chess.Move) -> None:
                self.best_move = best

            def analyse(self, board: chess.Board) -> EngineResult:
                if not board.move_stack:
                    return EngineResult(best_move=self.best_move, score_cp=100, depth=12)
                last_move = board.move_stack[-1]
                if last_move == self.best_move:
                    return EngineResult(best_move=self.best_move, score_cp=0, depth=12)
                return EngineResult(best_move=self.best_move, score_cp=-50, depth=12)

        result = analyze_position(position, StubEngine(best_move))

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "hanging_piece")
        self.assertEqual(outcome_row["result"], "unclear")

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "hanging_piece_unclear.duckdb")
        init_schema(conn)
        position_ids = insert_positions(conn, [position])
        tactic_row["position_id"] = position_ids[0]

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored_outcome = conn.execute(
            "SELECT result, user_uci FROM tactic_outcomes WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored_outcome[0], "unclear")
        self.assertEqual(stored_outcome[1], position["uci"])

    def test_fork_missed_reclassified_failed_attempt(self) -> None:
        class StubEngine:
            def __init__(self) -> None:
                self.calls = 0

            def analyse(self, board: chess.Board) -> EngineResult:
                self.calls += 1
                score_cp = 200
                if board.piece_at(chess.D6) == chess.Piece(chess.KNIGHT, chess.WHITE):
                    score_cp = 200
                elif board.piece_at(chess.E7) == chess.Piece(chess.KNIGHT, chess.WHITE):
                    score_cp = -150
                return EngineResult(
                    best_move=chess.Move.from_uci("f5e7"),
                    score_cp=score_cp,
                    depth=12,
                    mate_in=None,
                )

        board = chess.Board(None)
        board.clear()
        board.set_piece_at(chess.F5, chess.Piece(chess.KNIGHT, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.QUEEN, chess.BLACK))
        board.set_piece_at(chess.F7, chess.Piece(chess.ROOK, chess.BLACK))
        board.set_piece_at(chess.A1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.H8, chess.Piece(chess.KING, chess.BLACK))
        board.turn = chess.WHITE

        position = {
            "game_id": "unit-fork-failed-attempt",
            "fen": board.fen(),
            "uci": "f5d6",
        }

        result = analyze_position(position, StubEngine())

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "fork")
        self.assertEqual(outcome_row["result"], "failed_attempt")

    def test_fork_unclear_persists(self) -> None:
        class StubEngine:
            def __init__(self) -> None:
                self.calls = 0

            def analyse(self, board: chess.Board) -> EngineResult:
                self.calls += 1
                score_cp = 200
                if board.piece_at(chess.D6) == chess.Piece(chess.KNIGHT, chess.WHITE):
                    score_cp = 200
                elif board.piece_at(chess.E7) == chess.Piece(chess.KNIGHT, chess.WHITE):
                    score_cp = 180
                return EngineResult(
                    best_move=chess.Move.from_uci("f5e7"),
                    score_cp=score_cp,
                    depth=12,
                    mate_in=None,
                )

        board = chess.Board(None)
        board.clear()
        board.set_piece_at(chess.F5, chess.Piece(chess.KNIGHT, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.QUEEN, chess.BLACK))
        board.set_piece_at(chess.F7, chess.Piece(chess.ROOK, chess.BLACK))
        board.set_piece_at(chess.A1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.H8, chess.Piece(chess.KING, chess.BLACK))
        board.turn = chess.WHITE

        position = {
            "game_id": "unit-fork-unclear",
            "user": "unit",
            "source": "lichess",
            "fen": board.fen(),
            "ply": board.ply(),
            "move_number": board.fullmove_number,
            "side_to_move": "white",
            "uci": "f5d6",
            "san": board.san(chess.Move.from_uci("f5d6")),
            "clock_seconds": None,
            "is_legal": True,
        }

        result = analyze_position(position, StubEngine())

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "fork")
        self.assertEqual(outcome_row["result"], "unclear")

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "fork_unclear.duckdb")
        init_schema(conn)
        position_ids = insert_positions(conn, [position])
        tactic_row["position_id"] = position_ids[0]

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored_outcome = conn.execute(
            "SELECT result, user_uci FROM tactic_outcomes WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored_outcome[0], "unclear")
        self.assertEqual(stored_outcome[1], position["uci"])

    def test_discovered_attack_unclear_reclassified_failed_attempt(self) -> None:
        class StubEngine:
            def __init__(self) -> None:
                self.calls = 0

            def analyse(self, board: chess.Board) -> EngineResult:
                self.calls += 1
                if self.calls == 1:
                    return EngineResult(
                        best_move=chess.Move.from_uci("a2c1"),
                        score_cp=0,
                        depth=12,
                        mate_in=None,
                    )
                if self.calls == 2:
                    return EngineResult(
                        best_move=None,
                        score_cp=50,
                        depth=12,
                        mate_in=None,
                    )
                return EngineResult(
                    best_move=None,
                    score_cp=-10,
                    depth=12,
                    mate_in=None,
                )

        board = chess.Board(None)
        board.clear()
        board.set_piece_at(chess.H1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.A1, chess.Piece(chess.ROOK, chess.WHITE))
        board.set_piece_at(chess.A2, chess.Piece(chess.KNIGHT, chess.WHITE))
        board.set_piece_at(chess.G2, chess.Piece(chess.PAWN, chess.WHITE))
        board.set_piece_at(chess.H8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.A8, chess.Piece(chess.QUEEN, chess.BLACK))
        board.turn = chess.WHITE

        position = {
            "game_id": "unit-discovered-attack-failed-attempt",
            "fen": board.fen(),
            "uci": "a2b4",
        }

        result = analyze_position(position, StubEngine())

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "discovered_attack")
        self.assertEqual(outcome_row["result"], "failed_attempt")


if __name__ == "__main__":
    unittest.main()
