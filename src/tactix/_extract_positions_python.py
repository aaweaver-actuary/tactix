"""Pure-Python PGN position extractor."""

from __future__ import annotations

from tactix._build_pgn_context import _build_pgn_context
from tactix._iter_position_contexts import _iter_position_contexts
from tactix._normalize_side_filter import _normalize_side_filter
from tactix._resolve_game_context import _resolve_game_context


def _extract_positions_python(
    pgn: str,
    user: str,
    source: str,
    game_id: str | None = None,
    side_to_move_filter: str | None = None,
) -> list[dict[str, object]]:
    """Extract positions from PGN text using the Python path."""
    ctx = _build_pgn_context(pgn, user, source, game_id, side_to_move_filter)
    game_context = _resolve_game_context(ctx)
    if game_context is None:
        return []
    game, board, user_color = game_context
    side_filter = _normalize_side_filter(ctx.side_to_move_filter)
    return _iter_position_contexts(ctx, game, board, user_color, side_filter)
