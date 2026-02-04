"""Conditionally upsert a raw PGN row."""

from collections.abc import Mapping
from dataclasses import dataclass

from tactix._build_pgn_upsert_plan import _build_pgn_upsert_plan
from tactix._has_game_source import _has_game_source
from tactix._insert_raw_pgn_row import _insert_raw_pgn_row
from tactix._latest_pgn_metadata import _latest_pgn_metadata
from tactix._parse_game_source import _parse_game_source
from tactix._record_upsert_result import (
    _record_upsert_result,
)
from tactix.PgnUpsertPlan import PgnUpsertPlan


@dataclass(frozen=True)
class _RawPgnUpsertContext:
    cur: object
    key: tuple[str, str]
    row: Mapping[str, object]
    latest_meta: tuple[str | None, int]
    latest_cache: dict[tuple[str, str], tuple[str | None, int]]


def _maybe_upsert_raw_pgn_row(
    cur,
    row: Mapping[str, object],
    latest_cache: dict[tuple[str, str], tuple[str | None, int]],
) -> int:
    """Upsert a row if newer metadata is available."""
    game_id, source = _parse_game_source(row)
    if not _has_game_source(game_id, source):
        return 0
    key = (game_id, source)
    latest_hash, latest_version = _latest_pgn_metadata(cur, key, latest_cache)
    plan = _build_pgn_upsert_plan(row, latest_hash, latest_version)
    context = _RawPgnUpsertContext(
        cur=cur,
        key=key,
        row=row,
        latest_meta=(latest_hash, latest_version),
        latest_cache=latest_cache,
    )
    return _apply_pgn_upsert_plan__raw_pgn_row(context, plan)


def _apply_pgn_upsert_plan__raw_pgn_row(
    context: _RawPgnUpsertContext,
    plan: PgnUpsertPlan | None,
) -> int:
    """Return the upsert outcome for a plan."""
    # Justification: the upsert path has to handle both skip and write branches.
    if plan is None:
        context.latest_cache[context.key] = context.latest_meta
        return 0
    game_id, source = context.key
    _insert_raw_pgn_row(
        context.cur,
        game_id,
        source,
        context.row,
        plan,
    )
    return _record_upsert_result(
        context.cur,
        context.key,
        plan,
        context.latest_cache,
    )
