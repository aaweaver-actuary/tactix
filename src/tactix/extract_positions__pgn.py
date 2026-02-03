from __future__ import annotations

import os

from tactix._build_pgn_context import _build_pgn_context
from tactix._iter_position_contexts import _iter_position_contexts
from tactix._normalize_side_filter import _normalize_side_filter
from tactix._position_context_helpers import logger
from tactix._resolve_game_context import _resolve_game_context
from tactix.extract_positions_with_fallback__pgn import _extract_positions_with_fallback
from tactix.PgnContext import PgnContext


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


def extract_positions(
    pgn: str,
    user: str,
    source: str,
    game_id: str | None = None,
    side_to_move_filter: str | None = None,
) -> list[dict[str, object]]:
    return _extract_positions_with_fallback(
        pgn,
        user,
        source,
        game_id,
        side_to_move_filter,
        getenv=os.getenv,
        load_rust_extractor=_load_rust_extractor,
        call_rust_extractor=_call_rust_extractor,
        extract_positions_fallback=_extract_positions_fallback,
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
