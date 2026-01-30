import os
import shutil
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
from tactix.pgn_utils import extract_game_id, split_pgn_chunks
from tactix.stockfish_runner import StockfishEngine
from tactix.tactics_analyzer import analyze_position


def _discovered_check_fixture_position(fixture_path: Path) -> dict[str, object]:
    chunks = split_pgn_chunks(fixture_path.read_text())
    target_event = (
        os.getenv("TACTIX_DISCOVERED_CHECK_EVENT") or "discovered check"
    ).lower()
    for chunk in chunks:
        game = chess.pgn.read_game(StringIO(chunk))
        if not game:
            continue
        event = (game.headers.get("Event") or "").lower()
        if target_event not in event:
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


profile = os.getenv("TACTIX_CHESSCOM_PROFILE", "blitz")
fixture_name = os.getenv("TACTIX_DISCOVERED_CHECK_FIXTURE")
if fixture_name:
    fixture_path = Path(f"tests/fixtures/{fixture_name}")
else:
    fixture_path = Path(f"tests/fixtures/chesscom_{profile}_sample.pgn")

settings = Settings(
    source="chesscom",
    chesscom_user="chesscom",
    chesscom_profile=profile,
    stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
    stockfish_movetime_ms=60,
    stockfish_depth=None,
    stockfish_multipv=1,
)
settings.apply_chesscom_profile(profile)

position = _discovered_check_fixture_position(fixture_path)

override_game_id = os.getenv("TACTIX_DISCOVERED_CHECK_GAME_ID")
if override_game_id:
    position["game_id"] = override_game_id

conn = get_connection(Path("data") / "tactix.duckdb")
init_schema(conn)
if override_game_id:
    position_ids = insert_positions(conn, [position])
    position["position_id"] = position_ids[0]
else:
    row = conn.execute(
        """
        SELECT position_id, game_id, fen, uci
        FROM positions
        WHERE source = 'chesscom'
          AND uci = ?
          AND fen = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        [position["uci"], position["fen"]],
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
    raise SystemExit("No tactic result for discovered check fixture")

tactic_row, outcome_row = result
print("motif", tactic_row["motif"])
print("severity", tactic_row["severity"])
print("best_uci", tactic_row["best_uci"])

upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
print("seeded discovered check tactic into data/tactix.duckdb")
