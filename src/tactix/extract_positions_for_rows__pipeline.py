from __future__ import annotations

from tactix.config import Settings
from tactix.extract_positions__pgn import extract_positions
from tactix.resolve_side_to_move_filter__pipeline import _resolve_side_to_move_filter


def _extract_positions_for_rows(
    rows: list[dict[str, object]],
    settings: Settings,
) -> list[dict[str, object]]:
    positions: list[dict[str, object]] = []
    side_to_move_filter = _resolve_side_to_move_filter(settings)
    for row in rows:
        positions.extend(
            extract_positions(
                str(row.get("pgn", "")),
                str(row.get("user") or settings.user),
                str(row.get("source") or settings.source),
                game_id=str(row.get("game_id", "")),
                side_to_move_filter=side_to_move_filter,
            )
        )
    return positions
