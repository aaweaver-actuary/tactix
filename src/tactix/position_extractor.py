from __future__ import annotations

import re
from io import StringIO
from typing import Dict, List, Optional

import chess
import chess.pgn

from tactix.logging_utils import get_logger

logger = get_logger(__name__)

CLK_PATTERN = re.compile(r"%clk\s+(\d+):(\d+):(\d+)")


def _clock_from_comment(comment: str) -> Optional[float]:
    match = CLK_PATTERN.search(comment or "")
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds)


def _extract_positions_python(
    pgn: str, user: str, source: str, game_id: str | None = None
) -> List[Dict[str, object]]:
    game = chess.pgn.read_game(StringIO(pgn))
    if not game:
        logger.warning("Unable to parse PGN")
        return []

    white = game.headers.get("White", "").lower()
    black = game.headers.get("Black", "").lower()
    user_lower = user.lower()
    if user_lower not in {white, black}:
        logger.info("User %s not present in game headers; skipping", user)
        return []

    user_color = chess.WHITE if user_lower == white else chess.BLACK
    board = game.board()
    positions: List[Dict[str, object]] = []

    for node in game.mainline():
        move = node.move
        if move is None:
            continue
        is_user_to_move = board.turn == user_color
        if is_user_to_move:
            side_to_move = "white" if board.turn == chess.WHITE else "black"
            positions.append(
                {
                    "game_id": game_id or game.headers.get("Site", ""),
                    "user": user,
                    "source": source,
                    "fen": board.fen(),
                    "ply": board.ply(),
                    "move_number": board.fullmove_number,
                    "side_to_move": side_to_move,
                    "uci": move.uci(),
                    "san": board.san(move),
                    "clock_seconds": _clock_from_comment(node.comment or ""),
                }
            )
        board.push(move)

    logger.info("Extracted %s positions for user", len(positions))
    return positions


def extract_positions(
    pgn: str, user: str, source: str, game_id: str | None = None
) -> List[Dict[str, object]]:
    try:
        from tactix import _core
    except Exception:  # pragma: no cover - optional Rust extension
        return _extract_positions_python(pgn, user, source, game_id)

    rust_extractor = getattr(_core, "extract_positions", None)
    if rust_extractor is None:
        return _extract_positions_python(pgn, user, source, game_id)

    try:
        return rust_extractor(pgn, user, source, game_id)
    except Exception as exc:  # pragma: no cover - rust fallback
        logger.warning("Rust extractor failed; falling back to Python: %s", exc)
        return _extract_positions_python(pgn, user, source, game_id)
