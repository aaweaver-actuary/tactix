from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from io import StringIO

import chess
import chess.pgn

from tactix.utils.logger import get_logger

logger = get_logger(__name__)

CLK_PATTERN = re.compile(r"%clk\s+([0-9:.]+)")
CLOCK_PARTS_FULL = 3
CLOCK_PARTS_SHORT = 2


@dataclass
class PositionContext:
    game_id: str
    user: str
    source: str
    fen: str
    ply: int
    move_number: int
    side_to_move: str
    uci: str
    san: str
    clock_seconds: float | None
    is_legal: bool


@dataclass
class PgnContext:
    pgn: str
    user: str
    source: str
    game_id: str | None = None
    side_to_move_filter: str | None = None
    _game: chess.pgn.Game | None = None
    _board: chess.Board | None = None

    def __post_init__(self):
        self.user = self.user.lower()
        if self._game is None:
            self._get_game()

    def _get_game(self):
        if self._game is None:
            self._game = chess.pgn.read_game(StringIO(self.pgn))

    @property
    def game(self) -> chess.pgn.Game | None:
        self._get_game()
        return self._game

    @property
    def headers(self) -> dict[str, str]:
        self._get_game()
        if self._game is None:
            return {}
        return dict(self._game.headers)

    @property
    def fen(self) -> str | None:
        board = self.board
        if board is None:
            return None
        return board.fen()

    @property
    def board(self) -> chess.Board | None:
        if self._game is None:
            self._get_game()
        if self._game is None:
            return None
        if self._board is None:
            self._board = self._game.board()
        return self._board

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
    def side_to_move(self) -> str | None:
        board = self.board
        if board is None:
            return None
        return "white" if board.turn == chess.WHITE else "black"


def _clock_from_comment(comment: str) -> float | None:
    token = _clock_token(comment)
    if token is None:
        return None
    clock_parts = _normalize_clock_parts(token)
    if clock_parts is None:
        return None
    return _clock_to_seconds(*clock_parts)


def _clock_token(comment: str) -> str | None:
    match = CLK_PATTERN.search(comment or "")
    if not match:
        return None
    return match.group(1)


def _normalize_clock_parts(token: str) -> tuple[str, str, str] | None:
    parts = token.split(":")
    if len(parts) == CLOCK_PARTS_FULL:
        return parts[0], parts[1], parts[2]
    if len(parts) == CLOCK_PARTS_SHORT:
        return "0", parts[0], parts[1]
    return None


def _clock_to_seconds(hours: str, minutes: str, seconds: str) -> float | None:
    try:
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


def _build_pgn_context(
    pgn: str | PgnContext,
    user: str | None = None,
    source: str | None = None,
    game_id: str | None = None,
    side_to_move_filter: str | None = None,
) -> PgnContext:
    if isinstance(pgn, PgnContext):
        return pgn
    if user is None or source is None:
        raise ValueError("user and source are required when pgn is a string")
    return PgnContext(
        pgn=pgn,
        user=user,
        source=source,
        game_id=game_id,
        side_to_move_filter=side_to_move_filter,
    )


def _resolve_game_context(ctx: PgnContext) -> tuple[chess.pgn.Game, chess.Board, bool] | None:
    game = ctx.game
    if not game:
        logger.warning("Unable to parse PGN")
        return None
    if ctx.user not in {ctx.white, ctx.black}:
        logger.info("User %s not present in game headers; skipping", ctx.user)
        return None
    board = ctx.board
    if board is None:
        logger.warning("Unable to build board for PGN")
        return None
    user_color = _get_user_color(ctx.white, ctx.user)
    return game, board, user_color


def _iter_position_contexts(
    ctx: PgnContext,
    game: chess.pgn.Game,
    board: chess.Board,
    user_color: bool,
    side_filter: str | None,
) -> list[dict[str, object]]:
    positions: list[dict[str, object]] = []
    for node in game.mainline():
        position = _position_from_node(
            ctx,
            game,
            board,
            user_color,
            side_filter,
            node,
        )
        if position is not None:
            positions.append(position)
    return positions


def _position_from_node(
    ctx: PgnContext,
    game: chess.pgn.Game,
    board: chess.Board,
    user_color: bool,
    side_filter: str | None,
    node: chess.pgn.ChildNode,
) -> dict[str, object] | None:
    move = node.move
    if move is None:
        return None
    if _should_skip_for_turn(board, user_color):
        return _push_and_none(board, move)
    side_to_move = _side_from_turn(board.turn)
    if _should_skip_for_side(side_to_move, side_filter):
        return _push_and_none(board, move)
    if _is_illegal_move(board, move):
        logger.warning("Illegal move %s for FEN %s", move.uci(), board.fen())
        return _push_and_none(board, move)
    position = _build_position_context(ctx, game, board, node, move, side_to_move)
    board.push(move)
    return position


def _push_and_none(board: chess.Board, move: chess.Move) -> None:
    board.push(move)


def _should_skip_for_turn(board: chess.Board, user_color: bool) -> bool:
    return board.turn != user_color


def _should_skip_for_side(side_to_move: str, side_filter: str | None) -> bool:
    return bool(side_filter and side_to_move != side_filter)


def _is_illegal_move(board: chess.Board, move: chess.Move) -> bool:
    return move not in board.legal_moves


def _side_from_turn(turn: bool) -> str:
    return "white" if turn == chess.WHITE else "black"


def _build_position_context(
    ctx: PgnContext,
    game: chess.pgn.Game,
    board: chess.Board,
    node: chess.pgn.ChildNode,
    move: chess.Move,
    side_to_move: str,
) -> dict[str, object]:
    return asdict(
        PositionContext(
            game_id=ctx.game_id or game.headers.get("Site", ""),
            user=ctx.user,
            source=ctx.source,
            fen=board.fen(),
            ply=board.ply(),
            move_number=board.fullmove_number,
            side_to_move=side_to_move,
            uci=move.uci(),
            san=board.san(move),
            clock_seconds=_clock_from_comment(node.comment or ""),
            is_legal=True,
        )
    )


def _extract_positions_python(
    pgn: str | PgnContext,
    user: str | None = None,
    source: str | None = None,
    game_id: str | None = None,
    side_to_move_filter: str | None = None,
) -> list[dict[str, object]]:
    ctx = _build_pgn_context(
        pgn,
        user=user,
        source=source,
        game_id=game_id,
        side_to_move_filter=side_to_move_filter,
    )
    positions = _positions_from_context(ctx)
    logger.info("Extracted %s positions for user", len(positions))
    return positions


def _positions_from_context(ctx: PgnContext) -> list[dict[str, object]]:
    resolved = _resolve_game_context(ctx)
    if resolved is None:
        return []
    game, board, user_color = resolved
    normalized_side_filter = _normalize_side_filter(ctx.side_to_move_filter)
    return _iter_position_contexts(
        ctx,
        game,
        board,
        user_color,
        normalized_side_filter,
    )


def _get_user_color(white, user_lower):
    return chess.WHITE if user_lower == white else chess.BLACK


def extract_positions(
    pgn: str,
    user: str,
    source: str,
    game_id: str | None = None,
    side_to_move_filter: str | None = None,
) -> list[dict[str, object]]:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return _extract_positions_fallback(pgn, user, source, game_id, side_to_move_filter)
    rust_extractor = _load_rust_extractor()
    if rust_extractor is None:
        return _extract_positions_fallback(pgn, user, source, game_id, side_to_move_filter)
    return _call_rust_extractor(
        rust_extractor,
        pgn,
        user,
        source,
        game_id,
        side_to_move_filter,
    )


def _extract_positions_fallback(
    pgn: str,
    user: str,
    source: str,
    game_id: str | None,
    side_to_move_filter: str | None,
) -> list[dict[str, object]]:
    return _extract_positions_python(
        pgn,
        user,
        source,
        game_id,
        side_to_move_filter=side_to_move_filter,
    )


def _load_rust_extractor():
    try:
        from tactix import _core  # noqa: PLC0415
    except Exception:  # pragma: no cover - optional Rust extension
        return None
    return getattr(_core, "extract_positions", None)


def _call_rust_extractor(
    rust_extractor,
    pgn: str,
    user: str,
    source: str,
    game_id: str | None,
    side_to_move_filter: str | None,
) -> list[dict[str, object]]:
    try:
        return rust_extractor(pgn, user, source, game_id, side_to_move_filter)
    except Exception as exc:  # pragma: no cover - rust fallback
        logger.warning("Rust extractor failed; falling back to Python: %s", exc)
        return _extract_positions_fallback(pgn, user, source, game_id, side_to_move_filter)
