from __future__ import annotations


def _collect_game_ids(rows: list[dict[str, object]]) -> list[str]:
    return [str(row.get("game_id", "")) for row in rows if row.get("game_id")]
