from __future__ import annotations

import re
from io import StringIO
import os
from typing import Dict, List, Optional, Generator
from dataclasses import dataclass

import chess
import chess.pgn

from tactix.logging_utils import get_logger

logger = get_logger(__name__)

CLK_PATTERN = re.compile(r"%clk\s+([0-9:.]+)")


@dataclass
class PositionContext:
    game_id: str
    fen: str
    ply: int
    move_number: int
    side_to_move: str
    uci: str
    san: str
    clock_seconds: Optional[float]
    is_legal: bool


@dataclass
class PgnContext:
    pgn: str
    user: str
    source: str
    game_id: Optional[str] = None
    side_to_move_filter: Optional[str] = None
    _game: Optional[chess.pgn.Game] = None

    def __post_init__(self):
        self.user = self.user.lower()
        if self._game is None:
            self._get_game()

    def _get_game(self):
        if self._game is None:
            self._game = chess.pgn.read_game(StringIO(self.pgn))

    @property
    def game(self) -> Optional[chess.pgn.Game]:
        self._get_game()
        return self._game

    @property
    def headers(self) -> Dict[str, str]:
        self._get_game()
        if self._game is None:
            return {}
        return self._game.headers

    @property
    def fen(self) -> Optional[str]:
        board = self.board
        if board is None:
            return None
        return board.fen()

    @property
    def board(self) -> Optional[chess.Board]:
        if self._game is None:
            self._get_game()
        if self._game is None:
            return None
        return chess.Board(self.fen) if self.fen else self._game.board()

    @property
    def white(self) -> str:
        game = self.game
        if game is None:
            return ""
        return game.headers.get("White", "").lower()

    @property
    def black(self) -> str:
        game = self.game
        if game is None:
            return ""
        return game.headers.get("Black", "").lower()

    @property
    def ply(self) -> int:
        board = self.board
        if board is None:
            return 0
        return board.ply()

    @property
    def move_number(self) -> int:
        board = self.board
        if board is None:
            return 0
        return board.fullmove_number

    @property
    def side_to_move(self) -> Optional[str]:
        board = self.board
        if board is None:
            return None
        return "white" if board.turn == chess.WHITE else "black"

    def iter_nodes(self) -> Generator[chess.pgn.ChildNode, None, None]:
        game = self.game
        if game is None:
            return
        for node in game.mainline():
            yield node


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


def _extract_positions_python(ctx: PgnContext) -> List[Dict[str, object]]:
    game = chess.pgn.read_game(StringIO(ctx.pgn))
    if not game:
        logger.warning("Unable to parse PGN")
        return []

    if ctx.user not in {ctx.white, ctx.black}:
        logger.info("User %s not present in game headers; skipping", ctx.user)
        return []

    user_color = _get_user_color(ctx.white, ctx.user)

    positions = []
    normalized_side_filter = _normalize_side_filter(ctx.side_to_move_filter)

    for node in game.mainline():
        move = node.move
        if move is None:
            continue
        is_user_to_move = ctx.board.turn == user_color
        if not is_user_to_move:
            ctx.board.push(move)
            continue

        if normalized_side_filter and ctx.side_to_move != normalized_side_filter:
            ctx.board.push(move)
            continue
        is_legal = move in ctx.board.legal_moves
        if not is_legal:
            logger.warning("Illegal move %s for FEN %s", move.uci(), ctx.fen)
            ctx.board.push(move)
            continue
        positions.append(
            PositionContext(
                game_id=ctx.game_id or game.headers.get("Site", ""),
                user=ctx.user,
                source=ctx.source,
                fen=ctx.fen,
                ply=ctx.ply,
                move_number=ctx.move_number,
                side_to_move=ctx.side_to_move,
                uci=move.uci(),
                san=ctx.board.san(move),
                clock_seconds=_clock_from_comment(node.comment or ""),
                is_legal=is_legal,
            )
        )
        ctx.board.push(move)

    logger.info("Extracted %s positions for user", len(positions))
    return positions


def _get_user_color(white, user_lower):
    return chess.WHITE if user_lower == white else chess.BLACK


def _get_black_player_name(game):
    return game.headers.get("Black", "").lower()


def _get_white_player_name(game):
    return game.headers.get("White", "").lower()


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
