import logging
import shutil
from io import StringIO
from pathlib import Path

import chess
import chess.pgn

from tactix.config import Settings
from tactix.analyze_tactics__positions import MOTIF_DETECTORS
from tactix._infer_hanging_or_detected_motif import _infer_hanging_or_detected_motif
from tactix.analyze_position import analyze_position
from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.StockfishEngine import StockfishEngine
from tactix.utils.logger import set_level


def first_move_position(path: Path) -> tuple[chess.Board | None, chess.Move | None]:
    text = path.read_text()
    for chunk in text.split("\n\n\n"):
        game = chess.pgn.read_game(StringIO(chunk))
        if not game:
            continue
        fen = game.headers.get("FEN")
        board = chess.Board(fen) if fen else game.board()
        moves = list(game.mainline_moves())
        if not moves:
            continue
        return board, moves[0]
    return None, None


def first_move_position_with_label(
    path: Path,
    label: str,
) -> tuple[chess.Board | None, chess.Move | None]:
    text = path.read_text()
    for chunk in text.split("\n\n\n"):
        if label not in chunk:
            continue
        game = chess.pgn.read_game(StringIO(chunk))
        if not game:
            continue
        fen = game.headers.get("FEN")
        board = chess.Board(fen) if fen else game.board()
        moves = list(game.mainline_moves())
        if not moves:
            continue
        return board, moves[0]
    return None, None


def first_move_position_with_event(
    path: Path,
    event_substring: str,
) -> tuple[chess.Board | None, chess.Move | None]:
    text = path.read_text()
    for chunk in text.split("\n\n\n"):
        game = chess.pgn.read_game(StringIO(chunk))
        if not game:
            continue
        event = (game.headers.get("Event") or "").lower()
        if event_substring not in event:
            continue
        fen = game.headers.get("FEN")
        board = chess.Board(fen) if fen else game.board()
        moves = list(game.mainline_moves())
        if not moves:
            continue
        return board, moves[0]
    return None, None


def inspect(name: str, fixture: Path) -> list[str]:
    board, move = first_move_position(fixture)
    return inspect_move(name, board, move)


def inspect_labeled(name: str, fixture: Path, label: str) -> list[str]:
    board, move = first_move_position_with_label(fixture, label)
    return inspect_move(name, board, move)


def inspect_event(name: str, fixture: Path, event_substring: str) -> list[str]:
    board, move = first_move_position_with_event(fixture, event_substring)
    return inspect_move(name, board, move)


def inspect_move(
    name: str,
    board: chess.Board | None,
    move: chess.Move | None,
) -> list[str]:
    if board is None or move is None:
        return [f"{name} not found"]
    motif = MOTIF_DETECTORS.infer_motif(board, move)
    inferred = _infer_hanging_or_detected_motif(board, move, board.turn)
    capture = board.is_capture(move)
    board_after = board.copy()
    board_after.push(move)
    hanging_capture = BaseTacticDetector.is_hanging_capture(board, board_after, move, board.turn)
    lines = [
        " ".join(
            (
                name,
                "motif",
                motif,
                "inferred",
                inferred,
                "capture",
                str(capture),
                "hanging",
                str(hanging_capture),
                "mate",
                str(board_after.is_checkmate()),
            )
        )
    ]
    settings = Settings(
        stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
        stockfish_movetime_ms=60,
        stockfish_depth=12,
        stockfish_multipv=1,
    )
    position = {
        "game_id": f"debug-{name}",
        "position_id": 1,
        "fen": board.fen(),
        "uci": move.uci(),
    }
    with StockfishEngine(settings) as engine:
        result = analyze_position(position, engine, settings)
    if result is None:
        lines.append(f"{name} analyze_position none")
        return lines
    tactic_row, outcome_row = result
    lines.append(
        " ".join(
            (
                name,
                "analyze_position",
                str(tactic_row.get("motif")),
                "best_uci",
                str(tactic_row.get("best_uci")),
                "result",
                str(outcome_row.get("result")),
            )
        )
    )
    return lines


if __name__ == "__main__":
    set_level(logging.WARNING)
    logging.disable(logging.CRITICAL)
    base = Path("/Users/andy/tactix/tests/fixtures")
    results: list[str] = []
    results.extend(inspect("hangingpiece", base / "hangingpiece.pgn"))
    results.extend(inspect("skewer", base / "skewer.pgn"))
    results.extend(inspect("discoveredattack", base / "discoveredattack.pgn"))
    results.extend(
        inspect_labeled(
            "skewer-blitz-high",
            base / "chesscom_blitz_sample.pgn",
            "Blitz Fixture 6",
        )
    )
    results.extend(
        inspect_labeled(
            "mate-in-two-blitz",
            base / "chesscom_blitz_sample.pgn",
            "Blitz Fixture 4",
        )
    )
    results.extend(
        inspect_labeled(
            "fork-rapid",
            base / "chesscom_rapid_sample.pgn",
            "Rapid Fixture 5",
        )
    )
    results.extend(
        inspect_event(
            "discovered-attack-classical",
            base / "chesscom_classical_sample.pgn",
            "discovered attack",
        )
    )
    Path("/Users/andy/tactix/tmp_debug_motif_output.txt").write_text("\n".join(results) + "\n")
