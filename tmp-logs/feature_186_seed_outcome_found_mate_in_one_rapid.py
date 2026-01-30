import shutil
from pathlib import Path

import chess

from tactix.config import DEFAULT_RAPID_STOCKFISH_DEPTH, Settings
from tactix.db.duckdb_store import (
    get_connection,
    init_schema,
    upsert_tactic_with_outcome,
    update_metrics_summary,
    write_metrics_version,
)
from tactix.pgn_utils import split_pgn_chunks
from tactix.position_extractor import extract_positions
from tactix.stockfish_runner import StockfishEngine
from tactix.tactics_analyzer import analyze_position
from _seed_helpers import _ensure_position


if not shutil.which("stockfish"):
    raise SystemExit("Stockfish binary not on PATH")

fixture_path = Path("tests/fixtures/chesscom_rapid_sample.pgn")
chunks = split_pgn_chunks(fixture_path.read_text())
mate_pgn = next(chunk for chunk in chunks if "Rapid Fixture 3" in chunk)

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

positions = extract_positions(
    mate_pgn,
    settings.chesscom_user,
    settings.source,
    game_id="rapid-mate-1",
    side_to_move_filter="black",
)
mate_position = next(pos for pos in positions if pos["uci"] == "d8h4")

conn = get_connection(Path("data") / "tactix.duckdb")
init_schema(conn)

with StockfishEngine(settings) as engine:
    result = analyze_position(mate_position, engine, settings=settings)

if result is None:
    raise SystemExit("No tactic result for mate in one rapid fixture")

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
        raise SystemExit("No tactic result after forcing mate in one to best move")
    tactic_row, outcome_row = result

if outcome_row["result"] != "found":
    raise SystemExit("Expected found outcome for mate in one rapid fixture")

mate_position = _ensure_position(conn, mate_position)
tactic_row["position_id"] = mate_position["position_id"]
print("motif", tactic_row["motif"])
print("severity", tactic_row["severity"])
print("best_uci", tactic_row["best_uci"])

upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
update_metrics_summary(conn)
write_metrics_version(conn)
print("seeded mate in one (rapid) outcome into data/tactix.duckdb")
