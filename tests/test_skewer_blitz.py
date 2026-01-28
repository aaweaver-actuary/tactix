import shutil
import tempfile
import unittest
from io import StringIO
from pathlib import Path

import chess
import chess.pgn

from tactix.config import DEFAULT_BLITZ_STOCKFISH_DEPTH, Settings
from tactix.duckdb_store import (
    get_connection,
    init_schema,
    insert_positions,
    upsert_tactic_with_outcome,
)
from tactix.pgn_utils import extract_game_id, split_pgn_chunks
from tactix.stockfish_runner import StockfishEngine
from tactix.tactics_analyzer import analyze_position


def _skewer_fixture_position() -> dict[str, object]:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "skewer.pgn"
    chunks = split_pgn_chunks(fixture_path.read_text())
    for chunk in chunks:
        game = chess.pgn.read_game(StringIO(chunk))
        if not game:
            continue
        fen = game.headers.get("FEN")
        board = chess.Board(fen) if fen else game.board()
        moves = list(game.mainline_moves())
        if not moves:
            continue
        move = moves[0]
        side_to_move = "white" if board.turn == chess.WHITE else "black"
        return {
            "game_id": extract_game_id(chunk),
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
    raise AssertionError("No skewer fixture position found")


class SkewerBlitzTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_blitz_skewer_is_low_severity(self) -> None:
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
        self.assertEqual(settings.stockfish_depth, DEFAULT_BLITZ_STOCKFISH_DEPTH)

        position = _skewer_fixture_position()

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "skewer_blitz.duckdb")
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


if __name__ == "__main__":
    unittest.main()
