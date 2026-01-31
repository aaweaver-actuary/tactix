import shutil
from pathlib import Path

import chess

from tactix.config import Settings
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
    positions: list[dict[str, object]],
    engine: StockfishEngine,
    settings: Settings,
    expected_motif: str,
) -> tuple[dict[str, object], tuple[dict[str, object], dict[str, object]]]:
    for position in positions:
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
            if (
                outcome_row["result"] == "unclear"
                and tactic_row["motif"] == expected_motif
            ):
                return candidate, result
    raise SystemExit("No unclear outcome found for fork fixture")


def _fork_fixture_positions(profile: str, fixture_path: Path) -> list[dict[str, object]]:
    chunks = split_pgn_chunks(fixture_path.read_text())
    positions: list[dict[str, object]] = []
    for idx, chunk in enumerate(chunks, start=1):
        positions.extend(
            extract_positions(
                chunk,
                "chesscom",
                "chesscom",
                game_id=f"{profile}-fork-unclear-{idx}",
                side_to_move_filter=None,
            )
        )
    return positions


if not shutil.which("stockfish"):
    raise SystemExit("Stockfish binary not on PATH")

profiles = [
    ("rapid", Path("tests/fixtures/chesscom_rapid_sample.pgn")),
    ("blitz", Path("tests/fixtures/chesscom_blitz_sample.pgn")),
    ("bullet", Path("tests/fixtures/chesscom_bullet_sample.pgn")),
    ("classical", Path("tests/fixtures/chesscom_classical_sample.pgn")),
    ("correspondence", Path("tests/fixtures/chesscom_correspondence_sample.pgn")),
]

conn = get_connection(Path("data") / "tactix.duckdb")
init_schema(conn)

unclear_position = None
result = None
selected_profile = None

for profile, fixture_path in profiles:
    if not fixture_path.exists():
        continue
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
    positions = _fork_fixture_positions(profile, fixture_path)
    if not positions:
        continue
    with StockfishEngine(settings) as engine:
        try:
            unclear_position, result = _find_unclear_position(
                positions, engine, settings, "fork"
            )
        except SystemExit:
            unclear_position = None
            result = None
    if result is not None:
        selected_profile = profile
        break

if result is None or unclear_position is None or selected_profile is None:
    raise SystemExit("No unclear outcome found for fork fixture")

tactic_row, outcome_row = result
if outcome_row["result"] != "unclear":
    raise SystemExit("Expected unclear outcome for fork fixture")

unclear_position = _ensure_position(conn, unclear_position)
tactic_row["position_id"] = unclear_position["position_id"]

upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
update_metrics_summary(conn)
write_metrics_version(conn)
print(
    "seeded fork ({}) unclear outcome into data/tactix.duckdb".format(selected_profile)
)
