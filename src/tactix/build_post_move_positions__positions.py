"""Build post-move positions for hanging piece detection."""

from __future__ import annotations

import chess

from tactix.utils.logger import Logger

logger = Logger(__name__)


def build_post_move_positions__positions(
    positions: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return post-move positions derived from user move positions."""
    post_positions: list[dict[str, object]] = []
    for position in positions:
        post_position = _build_post_move_position(position)
        if post_position is not None:
            post_positions.append(post_position)
    return post_positions


def _build_post_move_position(
    position: dict[str, object],
) -> dict[str, object] | None:
    if not position.get("user_to_move", True):
        return None
    fen = str(position.get("fen") or "")
    uci = str(position.get("uci") or "")
    if not fen or not uci:
        return None
    board = _board_from_fen(fen)
    move = _move_from_uci(uci) if board is not None else None
    if board is None or move is None:
        return None
    if move not in board.legal_moves:
        logger.warning("Skipping post-move build for illegal move %s on FEN %s", uci, fen)
        return None
    board.push(move)
    return {
        **position,
        "fen": board.fen(),
        "ply": board.ply(),
        "move_number": board.fullmove_number,
        "side_to_move": "white" if board.turn == chess.WHITE else "black",
        "user_to_move": False,
        "is_legal": True,
    }


def _board_from_fen(fen: str) -> chess.Board | None:
    try:
        return chess.Board(fen)
    except ValueError:
        logger.warning("Skipping post-move build for invalid FEN: %s", fen)
        return None


def _move_from_uci(uci: str) -> chess.Move | None:
    try:
        return chess.Move.from_uci(uci)
    except ValueError:
        logger.warning("Skipping post-move build for invalid UCI: %s", uci)
        return None
