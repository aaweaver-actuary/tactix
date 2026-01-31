from __future__ import annotations

from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import FetchContext, GameRow
from tactix.lichess_client import write_checkpoint
from tactix.prepare_pgn__chess import latest_timestamp


def _update_lichess_checkpoint(
    settings: Settings,
    fetch_context: FetchContext,
    games: list[GameRow],
) -> tuple[int | None, int]:
    checkpoint_value = max(fetch_context.since_ms, latest_timestamp(games))
    write_checkpoint(settings.checkpoint_path, checkpoint_value)
    return checkpoint_value, checkpoint_value
