"""Parse game source identifiers from row mappings."""

from collections.abc import Mapping


def _parse_game_source(row: Mapping[str, object]) -> tuple[str, str]:
    game_id = str(row.get("game_id") or "")
    source = str(row.get("source") or "")
    return game_id, source
