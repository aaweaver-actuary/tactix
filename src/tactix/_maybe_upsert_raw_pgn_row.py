from collections.abc import Mapping

from tactix._build_pgn_upsert_plan import _build_pgn_upsert_plan
from tactix._has_game_source import _has_game_source
from tactix._insert_raw_pgn_row import _insert_raw_pgn_row
from tactix._latest_pgn_metadata import _latest_pgn_metadata
from tactix._parse_game_source import _parse_game_source
from tactix._record_upsert_result import (
    _record_upsert_result,
)


def _maybe_upsert_raw_pgn_row(
    cur,
    row: Mapping[str, object],
    latest_cache: dict[tuple[str, str], tuple[str | None, int]],
) -> int:
    game_id, source = _parse_game_source(row)
    if not _has_game_source(game_id, source):
        return 0
    key = (game_id, source)
    latest_hash, latest_version = _latest_pgn_metadata(cur, key, latest_cache)
    plan = _build_pgn_upsert_plan(row, latest_hash, latest_version)
    if plan is None:
        latest_cache[key] = (latest_hash, latest_version)
        return 0
    _insert_raw_pgn_row(cur, game_id, source, row, plan)
    return _record_upsert_result(cur, key, plan, latest_cache)
