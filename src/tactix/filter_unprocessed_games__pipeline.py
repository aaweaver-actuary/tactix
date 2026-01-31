from __future__ import annotations

from tactix.define_pipeline_state__pipeline import ZERO_COUNT


def _filter_unprocessed_games(
    raw_pgns: list[dict[str, object]],
    position_counts: dict[str, int],
) -> list[dict[str, object]]:
    return [
        row
        for row in raw_pgns
        if position_counts.get(str(row.get("game_id")), ZERO_COUNT) == ZERO_COUNT
    ]
