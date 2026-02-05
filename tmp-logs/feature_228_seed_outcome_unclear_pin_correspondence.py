from io import StringIO
from pathlib import Path

import chess
import chess.pgn

from tactix.config import Settings
from tactix.db.duckdb_store import (
    get_connection,
    init_schema,
    upsert_tactic_with_outcome,
    update_metrics_summary,
    write_metrics_version,
)
from tactix.pgn_utils import split_pgn_chunks
from tactix.stockfish_runner import EngineResult
from tactix.analyze_position import analyze_position
from _seed_helpers import _ensure_position


def _build_unclear_result(
    position: dict[str, object],
    best_move: chess.Move,
) -> tuple[dict[str, object], dict[str, object]]:
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
    if result is None:
        raise SystemExit("No result for pin unclear seed position")
    tactic_row, outcome_row = result
    if tactic_row["motif"] != "pin" or outcome_row["result"] != "unclear":
        raise SystemExit("Expected unclear pin outcome for seed position")
    return tactic_row, outcome_row


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


def _pin_fixture_positions() -> list[dict[str, object]]:
    fixture_path = Path("tests/fixtures/pin.pgn")
    chunks = split_pgn_chunks(fixture_path.read_text())
    positions: list[dict[str, object]] = []
    for idx, chunk in enumerate(chunks, start=1):
        position = _first_move_position(chunk, game_id=f"pin-unclear-{idx}")
        if position:
            positions.append(position)
    return positions


settings = Settings(
    source="chesscom",
    chesscom_user="chesscom",
    chesscom_profile="correspondence",
    stockfish_path=Path("stockfish"),
    stockfish_movetime_ms=60,
    stockfish_depth=None,
    stockfish_multipv=1,
)
settings.apply_chesscom_profile("correspondence")

positions = _pin_fixture_positions()
if not positions:
    raise SystemExit("No pin fixture positions found")

conn = get_connection(Path("data") / "tactix.duckdb")
init_schema(conn)

unclear_position = positions[0]
board = chess.Board(str(unclear_position["fen"]))
user_move = chess.Move.from_uci(str(unclear_position["uci"]))
best_move = next(move for move in board.legal_moves if move != user_move)
tactic_row, outcome_row = _build_unclear_result(unclear_position, best_move)

unclear_position = _ensure_position(conn, unclear_position)
tactic_row["position_id"] = unclear_position["position_id"]

upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
update_metrics_summary(conn)
write_metrics_version(conn)
print("seeded pin (correspondence) unclear outcome into data/tactix.duckdb")
