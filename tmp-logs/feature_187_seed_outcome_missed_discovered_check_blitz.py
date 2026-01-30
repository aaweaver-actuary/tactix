import shutil
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
    update_metrics_summary,
    write_metrics_version,
)
from tactix.pgn_utils import extract_game_id, split_pgn_chunks
from tactix.stockfish_runner import StockfishEngine
from tactix.tactics_analyzer import analyze_position


def _ensure_position(conn, position: dict[str, object]) -> dict[str, object]:
    row = conn.execute(
        """
        SELECT position_id, game_id, fen, uci
        FROM positions
        WHERE source = ?
          AND game_id = ?
          AND uci = ?
          AND fen = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        [position["source"], position["game_id"], position["uci"], position["fen"]],
    ).fetchone()
    if row:
        position["position_id"] = row[0]
        return position
    position_ids = insert_positions(conn, [position])
    position["position_id"] = position_ids[0]
    return position


def _find_missed_position(
    position: dict[str, object],
    engine: StockfishEngine,
    settings: Settings,
    expected_motif: str,
) -> tuple[dict[str, object], tuple[dict[str, object], dict[str, object]]]:
    board = chess.Board(str(position["fen"]))
    best_move = engine.analyse(board).best_move
    for move in board.legal_moves:
        if best_move is not None and move == best_move:
            continue
        candidate = dict(position)
        candidate["uci"] = move.uci()
        try:
            candidate["san"] = board.san(move)
        except Exception:
            pass
        result = analyze_position(candidate, engine, settings=settings)
        if result is None:
            continue
        tactic_row, outcome_row = result
        if outcome_row["result"] == "missed" and tactic_row["motif"] == expected_motif:
            return candidate, result
    raise SystemExit("No missed outcome found for discovered check fixture")


def _discovered_check_fixture_position() -> dict[str, object]:
    fixture_path = Path("tests/fixtures/chesscom_blitz_sample.pgn")
    chunks = split_pgn_chunks(fixture_path.read_text())
    discovered_chunk = next(
        chunk for chunk in chunks if "Discovered Check High" in chunk
    )
    game = chess.pgn.read_game(StringIO(discovered_chunk))
    if not game:
        raise SystemExit("No discovered check high fixture game found")
    fen = game.headers.get("FEN")
    board = chess.Board(fen) if fen else game.board()
    moves = list(game.mainline_moves())
    if not moves:
        raise SystemExit("No moves in discovered check high fixture")
    move = moves[0]
    side_to_move = "white" if board.turn == chess.WHITE else "black"
    return {
        "game_id": "blitz-discovered-check-high",
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


if not shutil.which("stockfish"):
    raise SystemExit("Stockfish binary not on PATH")

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
assert settings.stockfish_depth == DEFAULT_BLITZ_STOCKFISH_DEPTH

position = _discovered_check_fixture_position()

conn = get_connection(Path("data") / "tactix.duckdb")
init_schema(conn)

with StockfishEngine(settings) as engine:
    missed_position, result = _find_missed_position(
        position, engine, settings, "discovered_check"
    )

tactic_row, outcome_row = result
if outcome_row["result"] != "missed":
    raise SystemExit("Expected missed outcome for discovered check blitz fixture")

missed_position = _ensure_position(conn, missed_position)
tactic_row["position_id"] = missed_position["position_id"]

upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
update_metrics_summary(conn)
write_metrics_version(conn)
print("seeded discovered check (blitz) missed outcome into data/tactix.duckdb")
