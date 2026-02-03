import shutil
from pathlib import Path

from tactix.config import DEFAULT_CLASSICAL_STOCKFISH_DEPTH, Settings
from tactix.db.duckdb_store import (
    get_connection,
    init_schema,
    insert_positions,
    upsert_tactic_with_outcome,
)
from tactix.pgn_utils import split_pgn_chunks
from tactix.extract_positions import extract_positions
from tactix.StockfishEngine import StockfishEngine
from tactix.tactics_analyzer import analyze_position

fixture_path = Path("tests/fixtures/chesscom_classical_fork_sample.pgn")
chunks = split_pgn_chunks(fixture_path.read_text())
fork_pgn = chunks[0]

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
    game_id="classical-fork",
    side_to_move_filter="black",
)
fork_position = next(pos for pos in positions if pos["uci"] == "f4e2")

conn = get_connection(Path("data") / "tactix.duckdb")
init_schema(conn)
row = conn.execute(
    """
    SELECT p.position_id, p.game_id, p.fen, p.uci
    FROM positions p
    LEFT JOIN raw_pgns r ON r.game_id = p.game_id AND r.source = p.source
    WHERE p.source = 'chesscom'
      AND p.uci = 'f4e2'
      AND COALESCE(r.time_control, 'unknown') = '1800'
    ORDER BY p.created_at DESC
    LIMIT 1
    """
).fetchone()

if row:
    position_id, game_id, fen, uci = row
    fork_position = {
        "position_id": position_id,
        "game_id": game_id,
        "fen": fen,
        "uci": uci,
    }
else:
    position_ids = insert_positions(conn, [fork_position])
    fork_position["position_id"] = position_ids[0]

with StockfishEngine(settings) as engine:
    result = analyze_position(fork_position, engine, settings=settings)

if result is None:
    raise SystemExit("No tactic result for classical fork fixture")

tactic_row, outcome_row = result
print("motif", tactic_row["motif"])
print("severity", tactic_row["severity"])
print("best_uci", tactic_row["best_uci"])

upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
print("seeded classical fork tactic into data/tactix.duckdb")
