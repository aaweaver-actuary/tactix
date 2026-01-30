import os
import shutil
from io import StringIO
from pathlib import Path

import chess
import chess.pgn

from tactix.config import DEFAULT_CLASSICAL_STOCKFISH_DEPTH, Settings
from tactix.db.duckdb_store import (
    get_connection,
    init_schema,
    insert_positions,
    upsert_tactic_with_outcome,
)
from tactix.pgn_utils import split_pgn_chunks
from tactix.stockfish_runner import StockfishEngine
from tactix.tactics_analyzer import analyze_position


def _hanging_piece_fixture_position() -> dict[str, object]:
    fixture_path = Path("tests/fixtures/chesscom_classical_sample.pgn")
    chunks = split_pgn_chunks(fixture_path.read_text())
    hanging_chunk = next(
        chunk
        for chunk in chunks
        if "Classical Fixture 12 - Hanging Piece High" in chunk
    )
    game = chess.pgn.read_game(StringIO(hanging_chunk))
    if not game:
        raise SystemExit("No hanging piece fixture game found")
    fen = game.headers.get("FEN")
    board = chess.Board(fen) if fen else game.board()
    moves = list(game.mainline_moves())
    if not moves:
        raise SystemExit("No moves in hanging piece fixture")
    move = moves[0]
    side_to_move = "white" if board.turn == chess.WHITE else "black"
    return {
        "game_id": "classical-hanging-piece-high",
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


settings = Settings(
    source="chesscom",
    chesscom_user="chesscom",
    chesscom_profile="classical",
    stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
    stockfish_movetime_ms=180,
    stockfish_depth=None,
    stockfish_multipv=1,
)
settings.apply_chesscom_profile("classical")
assert settings.stockfish_depth == DEFAULT_CLASSICAL_STOCKFISH_DEPTH

position = _hanging_piece_fixture_position()

override_game_id = os.getenv("TACTIX_HANGING_PIECE_GAME_ID")
if override_game_id:
    position["game_id"] = override_game_id

conn = get_connection(Path("data") / "tactix.duckdb")
init_schema(conn)
row = conn.execute(
    """
    SELECT position_id, game_id, fen, uci
    FROM positions
    WHERE source = 'chesscom'
      AND game_id = ?
      AND uci = ?
      AND fen = ?
    ORDER BY created_at DESC
    LIMIT 1
    """,
    [position["game_id"], position["uci"], position["fen"]],
).fetchone()

if row:
    position_id, game_id, fen, uci = row
    position = {
        "position_id": position_id,
        "game_id": game_id,
        "fen": fen,
        "uci": uci,
    }
else:
    position_ids = insert_positions(conn, [position])
    position["position_id"] = position_ids[0]

with StockfishEngine(settings) as engine:
    result = analyze_position(position, engine, settings=settings)

if result is None:
    raise SystemExit("No tactic result for hanging piece classical fixture")

tactic_row, outcome_row = result
print("motif", tactic_row["motif"])
print("severity", tactic_row["severity"])
print("best_uci", tactic_row["best_uci"])

upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
print("seeded hanging piece classical high tactic into data/tactix.duckdb")
