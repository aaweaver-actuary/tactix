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


def _find_unclear_position(
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
        if outcome_row["result"] == "unclear" and tactic_row["motif"] == expected_motif:
            return candidate, result
    raise SystemExit("No unclear outcome found for mate in one fixture")


def _mate_in_one_fixture_position() -> dict[str, object]:
    fixture_path = Path("tests/fixtures/chesscom_rapid_sample.pgn")
    chunks = split_pgn_chunks(fixture_path.read_text())
    mate_pgn = next(chunk for chunk in chunks if "Rapid Fixture 3" in chunk)
    positions = extract_positions(
        mate_pgn,
        "chesscom",
        "chesscom",
        game_id="rapid-mate-1-unclear",
        side_to_move_filter="black",
    )
    return next(pos for pos in positions if pos["uci"] == "d8h4")


if not shutil.which("stockfish"):
    raise SystemExit("Stockfish binary not on PATH")

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

position = _mate_in_one_fixture_position()

conn = get_connection(Path("data") / "tactix.duckdb")
init_schema(conn)

with StockfishEngine(settings) as engine:
    unclear_position, result = _find_unclear_position(position, engine, settings, "mate")

tactic_row, outcome_row = result
if outcome_row["result"] != "unclear":
    raise SystemExit("Expected unclear outcome for mate in one rapid fixture")

unclear_position = _ensure_position(conn, unclear_position)
tactic_row["position_id"] = unclear_position["position_id"]

upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
update_metrics_summary(conn)
write_metrics_version(conn)
print("seeded mate in one (rapid) unclear outcome into data/tactix.duckdb")
