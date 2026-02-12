import shutil
import tempfile
import unittest
from pathlib import Path

import chess

from tactix.StockfishEngine import StockfishEngine
from tactix.analyze_position import analyze_position
from tactix.config import Settings
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.position_repository_provider import insert_positions


def _build_settings() -> Settings:
    settings = Settings(
        source="chesscom",
        chesscom_user="chesscom",
        chesscom_profile="blitz",
        stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
        stockfish_movetime_ms=60,
        stockfish_depth=None,
        stockfish_multipv=1,
    )
    settings.apply_chesscom_profile("blitz")
    return settings


def _analyze_position(position: dict[str, object]) -> tuple[dict[str, object], dict[str, object]] | None:
    settings = _build_settings()
    tmp_dir = Path(tempfile.mkdtemp())
    conn = get_connection(tmp_dir / "opp_hanging_piece_illegal.duckdb")
    init_schema(conn)
    position_ids = insert_positions(conn, [position])
    position["position_id"] = position_ids[0]

    with StockfishEngine(settings) as engine:
        return analyze_position(position, engine, settings=settings)


class OppHangingPieceIllegalCaptureTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_pinned_capture_does_not_create_hanging_piece(self) -> None:
        fen = "4r1k1/8/8/8/5q2/8/4N3/4K3 w - - 0 1"
        board = chess.Board(fen)
        user_move = chess.Move.from_uci("e1d1")
        position = {
            "game_id": "opp-hanging-illegal-pin",
            "user": "chesscom",
            "source": "chesscom",
            "fen": fen,
            "ply": board.ply(),
            "move_number": board.fullmove_number,
            "side_to_move": "white",
            "uci": user_move.uci(),
            "san": board.san(user_move),
            "clock_seconds": None,
            "is_legal": True,
        }

        result = _analyze_position(position)
        if result is None:
            return
        tactic_row, _ = result
        self.assertNotEqual(tactic_row.get("motif"), "hanging_piece")
        self.assertNotEqual(tactic_row.get("target_square"), "f4")

    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_illegal_capture_that_exposes_check_is_excluded(self) -> None:
        fen = "4r1k1/8/8/6q1/8/5N2/8/4K3 w - - 0 1"
        board = chess.Board(fen)
        user_move = chess.Move.from_uci("e1f2")
        position = {
            "game_id": "opp-hanging-illegal-check",
            "user": "chesscom",
            "source": "chesscom",
            "fen": fen,
            "ply": board.ply(),
            "move_number": board.fullmove_number,
            "side_to_move": "white",
            "uci": user_move.uci(),
            "san": board.san(user_move),
            "clock_seconds": None,
            "is_legal": True,
        }

        result = _analyze_position(position)
        if result is None:
            return
        tactic_row, _ = result
        self.assertNotEqual(tactic_row.get("motif"), "hanging_piece")
        self.assertNotEqual(tactic_row.get("target_square"), "g5")

    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_legal_capture_is_selected_over_illegal_candidate(self) -> None:
        fen = "4r1k1/1q6/8/8/5r2/8/4N1B1/4K3 w - - 0 1"
        board = chess.Board(fen)
        user_move = chess.Move.from_uci("e1d1")
        position = {
            "game_id": "opp-hanging-legal-target",
            "user": "chesscom",
            "source": "chesscom",
            "fen": fen,
            "ply": board.ply(),
            "move_number": board.fullmove_number,
            "side_to_move": "white",
            "uci": user_move.uci(),
            "san": board.san(user_move),
            "clock_seconds": None,
            "is_legal": True,
        }

        result = _analyze_position(position)
        self.assertIsNotNone(result)
        tactic_row, _ = result or ({}, {})
        self.assertEqual(tactic_row.get("motif"), "hanging_piece")
        self.assertEqual(tactic_row.get("target_piece"), "queen")
        self.assertEqual(tactic_row.get("target_square"), "b7")
        self.assertNotEqual(tactic_row.get("target_square"), "f4")


if __name__ == "__main__":
    unittest.main()
