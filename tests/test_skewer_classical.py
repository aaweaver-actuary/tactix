import shutil
import tempfile
import unittest
from io import StringIO
from pathlib import Path

import chess
import chess.pgn

from tactix.config import DEFAULT_CLASSICAL_STOCKFISH_DEPTH, Settings
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.position_repository_provider import insert_positions
from tactix.db.tactic_repository_provider import upsert_tactic_with_outcome
from tactix.pgn_utils import split_pgn_chunks
from tactix.StockfishEngine import StockfishEngine
from tactix.analyze_position import analyze_position
from tests.fixture_helpers import skewer_fixture_position
from tactix.tactic_scope import is_supported_motif


def _skewer_high_fixture_position() -> dict[str, object]:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "chesscom_classical_sample.pgn"
    chunks = split_pgn_chunks(fixture_path.read_text())
    skewer_chunk = next(chunk for chunk in chunks if "Classical Fixture 6" in chunk)
    game = chess.pgn.read_game(StringIO(skewer_chunk))
    if not game:
        raise AssertionError("No skewer high fixture game found")
    fen = game.headers.get("FEN")
    board = chess.Board(fen) if fen else game.board()
    moves = list(game.mainline_moves())
    if not moves:
        raise AssertionError("No moves in skewer high fixture")
    move = moves[0]
    side_to_move = "white" if board.turn == chess.WHITE else "black"
    return {
        "game_id": "classical-skewer-high",
        "user": "chesscom",
        "source": "chesscom",
        "fen": board.fen(),
        "ply": board.ply(),
        "move_number": board.fullmove_number,
        "side_to_move": side_to_move,
        "uci": move.uci(),
        "san": board.san(move),
        "clock_seconds": None,
        "is_legal": True,
    }


@unittest.skipUnless(is_supported_motif("skewer"), "Skewer disabled in current scope")
class SkewerClassicalTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_classical_skewer_is_low_severity(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="classical",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("classical")
        self.assertEqual(settings.stockfish_depth, DEFAULT_CLASSICAL_STOCKFISH_DEPTH)

        position = skewer_fixture_position()

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "skewer_classical.duckdb")
        init_schema(conn)
        position_ids = insert_positions(conn, [position])
        position["position_id"] = position_ids[0]

        with StockfishEngine(settings) as engine:
            result = analyze_position(position, engine, settings=settings)

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "skewer")
        self.assertGreater(tactic_row["severity"], 0)
        self.assertLessEqual(tactic_row["severity"], 1.0)
        self.assertTrue(tactic_row["best_uci"])

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored = conn.execute(
            "SELECT position_id, best_san, explanation FROM tactics WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored[0], position_ids[0])
        self.assertIsNotNone(stored[1])
        self.assertIn("Best line", stored[2] or "")

    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_classical_skewer_is_high_severity(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="classical",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("classical")
        self.assertEqual(settings.stockfish_depth, DEFAULT_CLASSICAL_STOCKFISH_DEPTH)

        skewer_position = _skewer_high_fixture_position()

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "skewer_classical_high.duckdb")
        init_schema(conn)
        position_ids = insert_positions(conn, [skewer_position])
        skewer_position["position_id"] = position_ids[0]

        with StockfishEngine(settings) as engine:
            result = analyze_position(skewer_position, engine, settings=settings)

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "skewer")
        self.assertEqual(tactic_row["game_id"], "classical-skewer-high")
        self.assertGreaterEqual(tactic_row["severity"], 1.5)
        self.assertLessEqual(outcome_row["eval_delta"], -150)
        self.assertTrue(tactic_row["best_uci"])

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored = conn.execute(
            "SELECT position_id, best_san, explanation FROM tactics WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored[0], position_ids[0])
        self.assertIsNotNone(stored[1])
        self.assertIn("Best line", stored[2] or "")


if __name__ == "__main__":
    unittest.main()
