import shutil
from pathlib import Path

import chess

from tactix.config import DEFAULT_BLITZ_STOCKFISH_DEPTH, Settings
from tactix.db.duckdb_store import (
    get_connection,
    init_schema,
    insert_positions,
    upsert_tactic_with_outcome,
    update_metrics_summary,
    write_metrics_version,
)
from tactix.pgn_utils import split_pgn_chunks
from tactix.position_extractor import extract_positions
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


if not shutil.which("stockfish"):
    raise SystemExit("Stockfish binary not on PATH")

fixture_path = Path("tests/fixtures/chesscom_blitz_sample.pgn")
chunks = split_pgn_chunks(fixture_path.read_text())
mate_pgn = next(chunk for chunk in chunks if "Blitz Fixture 4" in chunk)

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

positions = extract_positions(
    mate_pgn,
    settings.chesscom_user,
    settings.source,
    game_id="blitz-mate-2",
    side_to_move_filter="black",
)
mate_position = next(pos for pos in positions if pos["uci"] == "c5f2")

conn = get_connection(Path("data") / "tactix.duckdb")
init_schema(conn)

with StockfishEngine(settings) as engine:
    result = analyze_position(mate_position, engine, settings=settings)

if result is None:
    raise SystemExit("No tactic result for mate in two blitz fixture")

tactic_row, outcome_row = result
if outcome_row["result"] != "found" and tactic_row.get("best_uci"):
    mate_position["uci"] = tactic_row["best_uci"]
    try:
        board = chess.Board(mate_position["fen"])
        move = chess.Move.from_uci(mate_position["uci"])
        mate_position["san"] = board.san(move)
    except Exception:
        pass
    with StockfishEngine(settings) as engine:
        result = analyze_position(mate_position, engine, settings=settings)
    if result is None:
        raise SystemExit("No tactic result after forcing mate in two to best move")
    tactic_row, outcome_row = result

if outcome_row["result"] != "found":
    raise SystemExit("Expected found outcome for mate in two blitz fixture")

mate_position = _ensure_position(conn, mate_position)
tactic_row["position_id"] = mate_position["position_id"]
print("motif", tactic_row["motif"])
print("severity", tactic_row["severity"])
print("best_uci", tactic_row["best_uci"])

upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
update_metrics_summary(conn)
write_metrics_version(conn)
print("seeded mate in two (blitz) outcome into data/tactix.duckdb")
