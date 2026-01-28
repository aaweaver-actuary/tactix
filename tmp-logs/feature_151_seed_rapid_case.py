import shutil
from io import StringIO
from pathlib import Path

import chess
import chess.pgn

from tactix.config import DEFAULT_RAPID_STOCKFISH_DEPTH, Settings
from tactix.duckdb_store import (
    get_connection,
    init_schema,
    insert_positions,
    upsert_tactic_with_outcome,
)
from tactix.pgn_utils import extract_game_id, split_pgn_chunks
from tactix.stockfish_runner import StockfishEngine
from tactix.tactics_analyzer import analyze_position


def _discovered_attack_fixture_position() -> dict[str, object]:
    fixture_path = Path("tests/fixtures/chesscom_rapid_sample.pgn")
    chunks = split_pgn_chunks(fixture_path.read_text())
    for chunk in chunks:
        game = chess.pgn.read_game(StringIO(chunk))
        if not game:
            continue
        event = (game.headers.get("Event") or "").lower()
        if "discovered attack" not in event:
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
    raise SystemExit("No discovered attack rapid fixture position found")


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
assert settings.stockfish_depth == DEFAULT_RAPID_STOCKFISH_DEPTH

position = _discovered_attack_fixture_position()
desired_game_id = position["game_id"]

conn = get_connection(Path("data") / "tactix.duckdb")
init_schema(conn)
row = conn.execute(
    """
    SELECT position_id, game_id, fen, uci
    FROM positions
    WHERE source = 'chesscom'
      AND uci = ?
      AND fen = ?
      AND game_id = ?
    ORDER BY created_at DESC
    LIMIT 1
    """,
    [position["uci"], position["fen"], desired_game_id],
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
    raise SystemExit("No tactic result for discovered attack rapid fixture")

tactic_row, outcome_row = result
print("motif", tactic_row["motif"])
print("severity", tactic_row["severity"])
print("best_uci", tactic_row["best_uci"])

upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
print("seeded discovered attack rapid tactic into data/tactix.duckdb")