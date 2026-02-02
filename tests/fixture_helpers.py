from __future__ import annotations

from contextlib import suppress
from io import StringIO
from pathlib import Path

import chess
import chess.pgn

from tactix.config import Settings
from tactix.pgn_utils import extract_game_id, split_pgn_chunks
from tactix.stockfish_runner import StockfishEngine
from tactix.tactics_analyzer import analyze_position


def _first_move_position(chunk: str, *, game_id: str | None = None) -> dict[str, object] | None:
    game = chess.pgn.read_game(StringIO(chunk))
    if not game:
        return None
    fen = game.headers.get("FEN")
    board = chess.Board(fen) if fen else game.board()
    moves = list(game.mainline_moves())
    if not moves:
        return None
    move = moves[0]
    side_to_move = "white" if board.turn == chess.WHITE else "black"
    return {
        "game_id": game_id or extract_game_id(chunk),
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


def pin_fixture_position() -> dict[str, object]:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "pin.pgn"
    chunks = split_pgn_chunks(fixture_path.read_text())
    for chunk in chunks:
        position = _first_move_position(chunk)
        if position:
            return position
    raise AssertionError("No pin fixture position found")


def pin_fixture_positions() -> list[dict[str, object]]:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "pin.pgn"
    chunks = split_pgn_chunks(fixture_path.read_text())
    positions: list[dict[str, object]] = []
    for chunk in chunks:
        position = _first_move_position(chunk)
        if position:
            positions.append(position)
    if not positions:
        raise AssertionError("No pin fixture positions found")
    return positions


def skewer_fixture_position() -> dict[str, object]:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "skewer.pgn"
    chunks = split_pgn_chunks(fixture_path.read_text())
    for chunk in chunks:
        position = _first_move_position(chunk)
        if position:
            return position
    raise AssertionError("No skewer fixture position found")


def discovered_attack_fixture_position() -> dict[str, object]:
    fixture_path = (
        Path(__file__).resolve().parent / "fixtures" / "chesscom_classical_sample.pgn"
    )
    chunks = split_pgn_chunks(fixture_path.read_text())
    for chunk in chunks:
        game = chess.pgn.read_game(StringIO(chunk))
        if not game:
            continue
        event = (game.headers.get("Event") or "").lower()
        if "discovered attack" not in event:
            continue
        position = _first_move_position(chunk)
        if position:
            return position
    raise AssertionError("No discovered attack fixture position found")


def hanging_piece_fixture_position(
    *,
    fixture_filename: str = "chesscom_blitz_sample.pgn",
    label: str = "Blitz Fixture 11 - Hanging Piece Low",
    game_id: str = "blitz-hanging-piece-low",
) -> dict[str, object]:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / fixture_filename
    chunks = split_pgn_chunks(fixture_path.read_text())
    hanging_chunk = next(chunk for chunk in chunks if label in chunk)
    position = _first_move_position(hanging_chunk, game_id=game_id)
    if not position:
        raise AssertionError("No hanging piece fixture game found")
    return position


def hanging_piece_high_fixture_position(
    *,
    fixture_filename: str = "chesscom_blitz_sample.pgn",
    label: str = "Blitz Fixture 12 - Hanging Piece High",
    game_id: str = "blitz-hanging-piece-high",
) -> dict[str, object]:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / fixture_filename
    chunks = split_pgn_chunks(fixture_path.read_text())
    hanging_chunk = next(chunk for chunk in chunks if label in chunk)
    position = _first_move_position(hanging_chunk, game_id=game_id)
    if not position:
        raise AssertionError("No hanging piece fixture game found")
    return position


def find_missed_position(
    position: dict[str, object],
    engine: StockfishEngine,
    settings: Settings,
    expected_motif: str,
) -> tuple[dict[str, object], tuple[dict[str, object], dict[str, object]]]:
    return _find_outcome_position(
        position,
        engine,
        settings,
        expected_motif,
        expected_result="missed",
        error_message="No missed outcome found for fixture position",
    )


def find_failed_attempt_position(
    position: dict[str, object],
    engine: StockfishEngine,
    settings: Settings,
    expected_motif: str,
) -> tuple[dict[str, object], tuple[dict[str, object], dict[str, object]]]:
    return _find_outcome_position(
        position,
        engine,
        settings,
        expected_motif,
        expected_result="failed_attempt",
        error_message="No failed_attempt outcome found for fixture position",
    )


def find_unclear_position(
    position: dict[str, object],
    engine: StockfishEngine,
    settings: Settings,
    expected_motif: str,
) -> tuple[dict[str, object], tuple[dict[str, object], dict[str, object]]]:
    return _find_outcome_position(
        position,
        engine,
        settings,
        expected_motif,
        expected_result="unclear",
        error_message="No unclear outcome found for fixture position",
    )


def _find_outcome_position(
    position: dict[str, object],
    engine: StockfishEngine,
    settings: Settings,
    expected_motif: str,
    *,
    expected_result: str,
    error_message: str,
) -> tuple[dict[str, object], tuple[dict[str, object], dict[str, object]]]:
    board = chess.Board(str(position["fen"]))
    best_move = engine.analyse(board).best_move
    for move in board.legal_moves:
        if best_move is not None and move == best_move:
            continue
        candidate = dict(position)
        candidate["uci"] = move.uci()
        with suppress(Exception):
            candidate["san"] = board.san(move)
        result = analyze_position(candidate, engine, settings=settings)
        if result is None:
            continue
        tactic_row, outcome_row = result
        if outcome_row["result"] == expected_result and tactic_row["motif"] == expected_motif:
            return candidate, result
    raise AssertionError(error_message)
