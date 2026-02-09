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


def append_positions_with_post_moves(
    positions: list[dict[str, object]],
    extracted: list[dict[str, object]],
    *,
    post_positions: list[dict[str, object]] | None = None,
) -> None:
    """Append extracted positions and their post-move counterparts."""
    positions.extend(extracted)
    built_post_positions = build_post_move_positions__positions(extracted)
    if post_positions is None:
        positions.extend(built_post_positions)
        return
    post_positions.extend(built_post_positions)


def _build_post_move_position(
    position: dict[str, object],
) -> dict[str, object] | None:
    context = _resolve_post_move_context(position)
    if context is None:
        return None
    board, move = context
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


def _resolve_post_move_context(
    position: dict[str, object],
) -> tuple[chess.Board, chess.Move] | None:
    fen_uci = _extract_fen_uci(position)
    if fen_uci is None:
        return None
    fen, uci = fen_uci
    board = _board_from_fen(fen)
    if board is None:
        return None
    move = _move_from_uci(uci)
    if move is None:
        return None
    if not _is_legal_post_move(board, move, uci, fen):
        return None
    return board, move


def _extract_fen_uci(position: dict[str, object]) -> tuple[str, str] | None:
    if not position.get("user_to_move", True):
        return None
    fen = str(position.get("fen") or "")
    uci = str(position.get("uci") or "")
    return _ensure_fen_uci(fen, uci)


def _ensure_fen_uci(fen: str, uci: str) -> tuple[str, str] | None:
    if not fen:
        return None
    if not uci:
        return None
    return fen, uci


def _is_legal_post_move(
    board: chess.Board,
    move: chess.Move,
    uci: str,
    fen: str,
) -> bool:
    if move in board.legal_moves:
        return True
    logger.warning("Skipping post-move build for illegal move %s on FEN %s", uci, fen)
    return False


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
