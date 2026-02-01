from __future__ import annotations

import tempfile
import unittest
from io import StringIO
from pathlib import Path

import chess
import chess.pgn

from tactix.config import Settings
from tactix.db.duckdb_store import (
    get_connection,
    init_schema,
    insert_positions,
    upsert_tactic_with_outcome,
)
from tactix.engine_result import EngineResult
from tactix.pgn_utils import split_pgn_chunks
from tactix.tactics_analyzer import analyze_position


def _first_move_position(chunk: str, game_id: str) -> dict[str, object] | None:
    game = chess.pgn.read_game(StringIO(chunk))
    if not game:
        return None
    fen = game.headers.get("FEN")
    board = chess.Board(fen) if fen else game.board()
    moves = list(game.mainline_moves())
    if not moves:
        return None
    move = moves[0]
    side_to_move = "white" if board.turn == chess.WHITE else "black"
    return {
        "game_id": game_id,
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


def _discovered_check_fixture_position() -> dict[str, object]:
    fixture_path = Path("tests/fixtures/chesscom_blitz_sample.pgn")
    chunks = split_pgn_chunks(fixture_path.read_text())
    for chunk in chunks:
        game = chess.pgn.read_game(StringIO(chunk))
        if not game:
            continue
        event = (game.headers.get("Event") or "").lower()
        if "discovered check" not in event:
            continue
        position = _first_move_position(chunk, game_id="blitz-discovered-check-unclear")
        if position:
            return position
    raise AssertionError("No discovered check fixture position found")


class DiscoveredCheckUnclearOutcomeTests(unittest.TestCase):
    def test_discovered_check_records_unclear_outcome(self) -> None:
        settings = Settings(source="chesscom", chesscom_user="chesscom", chesscom_profile="blitz")
        settings.apply_chesscom_profile("blitz")

        position = _discovered_check_fixture_position()
        board = chess.Board(str(position["fen"]))
        user_move = chess.Move.from_uci(str(position["uci"]))
        best_move = next(move for move in board.legal_moves if move != user_move)

        class StubEngine:
            def __init__(self, best: chess.Move) -> None:
                self.best_move = best

            def analyse(self, board: chess.Board) -> EngineResult:
                if not board.move_stack:
                    return EngineResult(best_move=self.best_move, score_cp=200, depth=12)
                last_move = board.move_stack[-1]
                if last_move == self.best_move:
                    return EngineResult(best_move=self.best_move, score_cp=-100, depth=12)
                return EngineResult(best_move=self.best_move, score_cp=-200, depth=12)

        result = analyze_position(position, StubEngine(best_move), settings=settings)
        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "discovered_check")
        self.assertEqual(outcome_row["result"], "unclear")

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "discovered_check_unclear.duckdb")
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


if __name__ == "__main__":
    unittest.main()
