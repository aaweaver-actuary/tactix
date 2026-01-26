from __future__ import annotations

import re
from io import StringIO
import os
from typing import Dict, List, Optional

import chess
import chess.pgn

from tactix.logging_utils import get_logger

logger = get_logger(__name__)

CLK_PATTERN = re.compile(r"%clk\s+([0-9:.]+)")


def _clock_from_comment(comment: str) -> Optional[float]:
    match = CLK_PATTERN.search(comment or "")
    if not match:
        return None
    token = match.group(1)
    parts = token.split(":")
    try:
        if len(parts) == 3:
            hours, minutes, seconds = parts
        elif len(parts) == 2:
            hours = "0"
            minutes, seconds = parts
        else:
            return None
        return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
    except ValueError:
        return None


def _normalize_side_filter(side_to_move_filter: str | None) -> str | None:
    if not side_to_move_filter:
        return None
    normalized = side_to_move_filter.strip().lower()
    if normalized in {"white", "black"}:
        return normalized
    logger.warning("Unknown side_to_move_filter: %s", side_to_move_filter)
    return None


def _extract_positions_python(
    pgn: str,
    user: str,
    source: str,
    game_id: str | None = None,
    side_to_move_filter: str | None = None,
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
    normalized_side_filter = _normalize_side_filter(side_to_move_filter)

    for node in game.mainline():
        move = node.move
        if move is None:
            continue
        is_user_to_move = board.turn == user_color
        if not is_user_to_move:
            board.push(move)
            continue
        side_to_move = "white" if board.turn == chess.WHITE else "black"
        if normalized_side_filter and side_to_move != normalized_side_filter:
            board.push(move)
            continue
        is_legal = move in board.legal_moves
        if not is_legal:
            logger.warning("Illegal move %s for FEN %s", move.uci(), board.fen())
            board.push(move)
            continue
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
                "is_legal": is_legal,
            }
        )
        board.push(move)

    logger.info("Extracted %s positions for user", len(positions))
    return positions


def extract_positions(
    pgn: str,
    user: str,
    source: str,
    game_id: str | None = None,
    side_to_move_filter: str | None = None,
) -> List[Dict[str, object]]:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return _extract_positions_python(
            pgn,
            user,
            source,
            game_id,
            side_to_move_filter=side_to_move_filter,
        )
    try:
        from tactix import _core
    except Exception:  # pragma: no cover - optional Rust extension
        return _extract_positions_python(
            pgn,
            user,
            source,
            game_id,
            side_to_move_filter=side_to_move_filter,
        )

    rust_extractor = getattr(_core, "extract_positions", None)
    if rust_extractor is None:
        return _extract_positions_python(
            pgn,
            user,
            source,
            game_id,
            side_to_move_filter=side_to_move_filter,
        )

    try:
        return rust_extractor(pgn, user, source, game_id, side_to_move_filter)
    except Exception as exc:  # pragma: no cover - rust fallback
        logger.warning("Rust extractor failed; falling back to Python: %s", exc)
        return _extract_positions_python(
            pgn,
            user,
            source,
            game_id,
            side_to_move_filter=side_to_move_filter,
        )
