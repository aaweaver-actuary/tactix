import shutil
from io import StringIO
from pathlib import Path

import chess
import chess.pgn

from tactix.config import DEFAULT_BULLET_STOCKFISH_DEPTH, Settings
from tactix.db.duckdb_store import (
    get_connection,
    init_schema,
    upsert_tactic_with_outcome,
    update_metrics_summary,
    write_metrics_version,
)
from tactix.pgn_utils import extract_game_id, split_pgn_chunks
from tactix.StockfishEngine import StockfishEngine
from tactix.analyze_position import analyze_position
from _seed_helpers import _ensure_position


def _discovered_check_fixture_position() -> dict[str, object]:
    fixture_path = Path("tests/fixtures/discoveredcheck.pgn")
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
    raise SystemExit("No discovered check fixture position found")


if not shutil.which("stockfish"):
    raise SystemExit("Stockfish binary not on PATH")

settings = Settings(
    source="chesscom",
    chesscom_user="chesscom",
    chesscom_profile="bullet",
    stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
    stockfish_movetime_ms=60,
    stockfish_depth=None,
    stockfish_multipv=1,
)
settings.apply_chesscom_profile("bullet")
assert settings.stockfish_depth == DEFAULT_BULLET_STOCKFISH_DEPTH

position = _discovered_check_fixture_position()

conn = get_connection(Path("data") / "tactix.duckdb")
init_schema(conn)

with StockfishEngine(settings) as engine:
    result = analyze_position(position, engine, settings=settings)

if result is None:
    raise SystemExit("No tactic result for discovered check fixture")

tactic_row, outcome_row = result
if outcome_row["result"] != "found" and tactic_row.get("best_uci"):
    position["uci"] = tactic_row["best_uci"]
    try:
        board = chess.Board(position["fen"])
        move = chess.Move.from_uci(position["uci"])
        position["san"] = board.san(move)
    except Exception:
        pass
    with StockfishEngine(settings) as engine:
        result = analyze_position(position, engine, settings=settings)
    if result is None:
        raise SystemExit("No tactic result after forcing discovered check to best move")
    tactic_row, outcome_row = result

if outcome_row["result"] != "found":
    raise SystemExit("Expected found outcome for discovered check bullet fixture")

position = _ensure_position(conn, position)
tactic_row["position_id"] = position["position_id"]
print("motif", tactic_row["motif"])
print("severity", tactic_row["severity"])
print("best_uci", tactic_row["best_uci"])

upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
update_metrics_summary(conn)
write_metrics_version(conn)
print("seeded discovered check (bullet) outcome into data/tactix.duckdb")
