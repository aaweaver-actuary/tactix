"""Extract positions from raw PGN rows."""

from __future__ import annotations

from tactix.app.use_cases.pipeline_support import _resolve_side_to_move_filter
from tactix.build_post_move_positions__positions import (
    build_post_move_positions__positions,
)
from tactix.config import Settings
from tactix.extract_positions__pgn import extract_positions


def _extract_positions_for_rows(
    rows: list[dict[str, object]],
    settings: Settings,
) -> list[dict[str, object]]:
    """Return extracted positions for the given rows."""
    positions: list[dict[str, object]] = []
    side_to_move_filter = _resolve_side_to_move_filter(settings)
    for row in rows:
        extracted = extract_positions(
            str(row.get("pgn", "")),
            str(row.get("user") or settings.user),
            str(row.get("source") or settings.source),
            game_id=str(row.get("game_id", "")),
            side_to_move_filter=side_to_move_filter,
        )
        positions.extend(extracted)
        positions.extend(build_post_move_positions__positions(extracted))
    return positions
