import shutil
from datetime import datetime, timezone
from pathlib import Path

from tactix.config import DEFAULT_CLASSICAL_STOCKFISH_DEPTH, Settings
from tactix.duckdb_store import (
    delete_game_rows,
    get_connection,
    init_schema,
    insert_positions,
    upsert_raw_pgns,
    upsert_tactic_with_outcome,
)
from tactix.pgn_utils import split_pgn_chunks
from tactix.position_extractor import extract_positions
from tactix.stockfish_runner import StockfishEngine
from tactix.tactics_analyzer import analyze_position

fixture_path = Path("tests/fixtures/chesscom_classical_sample.pgn")
chunks = split_pgn_chunks(fixture_path.read_text())
fork_pgn = next(chunk for chunk in chunks if "Classical Fixture 5" in chunk)

settings = Settings(
    source="chesscom",
    chesscom_user="chesscom",
    chesscom_profile="classical",
    stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
    stockfish_movetime_ms=60,
    stockfish_depth=None,
    stockfish_multipv=1,
)
settings.apply_chesscom_profile("classical")
assert settings.stockfish_depth == DEFAULT_CLASSICAL_STOCKFISH_DEPTH

positions = extract_positions(
    fork_pgn,
    settings.chesscom_user,
    settings.source,
    game_id="classical-fork-low",
    side_to_move_filter="black",
)
fork_position = next(pos for pos in positions if pos["uci"] == "f4e2")

conn = get_connection(Path("data") / "tactix.duckdb")
init_schema(conn)

# Ensure a fresh game_id so we keep the high-severity fork row intact.
delete_game_rows(conn, ["classical-fork-low"])

upsert_raw_pgns(
    conn,
    [
        {
            "game_id": "classical-fork-low",
            "user": settings.chesscom_user,
            "source": settings.source,
            "fetched_at": datetime.now(timezone.utc),
            "pgn": fork_pgn,
            "last_timestamp_ms": 0,
            "cursor": None,
        }
    ],
)

position_ids = insert_positions(conn, [fork_position])
fork_position["position_id"] = position_ids[0]

with StockfishEngine(settings) as engine:
    result = analyze_position(fork_position, engine, settings=settings)

if result is None:
    raise SystemExit("No tactic result for classical fork low severity fixture")

tactic_row, outcome_row = result
print("motif", tactic_row["motif"])
print("severity", tactic_row["severity"])
print("best_uci", tactic_row["best_uci"])

upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
print("seeded classical low severity fork tactic into data/tactix.duckdb")
