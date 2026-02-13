import tempfile
import unittest
from pathlib import Path

import chess

from tactix.analyze_position import analyze_position
from tactix.build_post_move_positions__positions import (
    build_post_move_positions__positions,
)
from tactix.config import Settings
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.position_repository_provider import insert_positions
from tactix.db.tactic_repository_provider import upsert_tactic_with_outcome
from tactix.StockfishEngine import StockfishEngine


class UserHangingPiecePostMoveTests(unittest.TestCase):
    def test_user_hanging_piece_created_on_post_move_position(self) -> None:
        position = _build_user_hanging_piece_position()
        post_positions = build_post_move_positions__positions([position])
        self.assertEqual(len(post_positions), 1)
        post_position = post_positions[0]
        self.assertFalse(post_position.get("user_to_move", True))

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "user_hanging_post_move.duckdb")
        init_schema(conn)

        positions_to_insert = [position, post_position]
        position_ids = insert_positions(conn, positions_to_insert)
        for pos, pos_id in zip(positions_to_insert, position_ids, strict=False):
            pos["position_id"] = pos_id

        settings = Settings(source="lichess", lichess_user="unit")
        with StockfishEngine(settings) as engine:
            self.assertIsNone(analyze_position(position, engine, settings=settings))
            result = analyze_position(post_position, engine, settings=settings)

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "hanging_piece")
        self.assertEqual(outcome_row["result"], "missed")
        self.assertEqual(tactic_row["target_piece"], "pawn")
        self.assertEqual(tactic_row["target_square"], "e3")
        self.assertIn(tactic_row["confidence"], {"high", "medium"})
        self.assertEqual(tactic_row["position_id"], post_position["position_id"])

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        created_at = conn.execute(
            "SELECT created_at FROM tactics WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()[0]
        self.assertIsNotNone(created_at)

        with StockfishEngine(settings) as engine:
            rerun = analyze_position(post_position, engine, settings=settings)
        self.assertIsNotNone(rerun)
        tactic_row, outcome_row = rerun
        upsert_tactic_with_outcome(conn, tactic_row, outcome_row)

        count = conn.execute(
            "SELECT COUNT(*) FROM tactics WHERE position_id = ?",
            [post_position["position_id"]],
        ).fetchone()[0]
        self.assertEqual(count, 1)


def _build_user_hanging_piece_position() -> dict[str, object]:
    board = chess.Board(None)
    board.clear()
    board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(chess.D1, chess.Piece(chess.QUEEN, chess.WHITE))
    board.set_piece_at(chess.E2, chess.Piece(chess.PAWN, chess.WHITE))
    board.set_piece_at(chess.A8, chess.Piece(chess.KING, chess.BLACK))
    board.set_piece_at(chess.E8, chess.Piece(chess.ROOK, chess.BLACK))
    board.turn = chess.WHITE

    move = chess.Move.from_uci("e2e3")
    return {
        "game_id": "unit-user-hanging-post-move",
        "user": "unit",
        "source": "lichess",
        "fen": board.fen(),
        "ply": board.ply(),
        "move_number": board.fullmove_number,
        "side_to_move": "white",
        "user_to_move": True,
        "uci": move.uci(),
        "san": board.san(move),
        "clock_seconds": None,
        "is_legal": True,
    }


if __name__ == "__main__":
    unittest.main()
