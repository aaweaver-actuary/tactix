"""Resolve the last chess.com timestamp for pipeline state."""

from __future__ import annotations

from tactix.define_pipeline_state__pipeline import FetchContext, GameRow
from tactix.latest_timestamp import latest_timestamp


def _resolve_chesscom_last_timestamp(
    fetch_context: FetchContext,
    games: list[GameRow],
    last_timestamp_value: int,
) -> int:
    if fetch_context.chesscom_result:
        return fetch_context.chesscom_result.last_timestamp_ms
    if games:
        return latest_timestamp(games) or last_timestamp_value
    return last_timestamp_value
