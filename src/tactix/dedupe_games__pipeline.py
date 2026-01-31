from __future__ import annotations

from tactix.pipeline_state__pipeline import GameRow


def _dedupe_games(rows: list[GameRow]) -> list[GameRow]:
    seen: set[tuple[str, str, int]] = set()
    deduped: list[GameRow] = []
    for game in rows:
        game_id = game["game_id"]
        source = game["source"]
        last_ts = game["last_timestamp_ms"]
        key = (game_id, source, last_ts)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(game)
    return deduped
