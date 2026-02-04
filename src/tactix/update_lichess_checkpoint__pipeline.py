"""Update Lichess checkpoint values after syncing games."""

from __future__ import annotations

from tactix.config import Settings
from tactix.FetchContext import FetchContext
from tactix.GameRow import GameRow
from tactix.latest_timestamp import latest_timestamp
from tactix.lichess_client import write_checkpoint


def _update_lichess_checkpoint(
    settings: Settings,
    fetch_context: FetchContext,
    games: list[GameRow],
) -> tuple[int | None, int]:
    """Persist and return the updated checkpoint value."""
    checkpoint_value = max(fetch_context.since_ms, latest_timestamp(games))
    write_checkpoint(settings.checkpoint_path, checkpoint_value)
    return checkpoint_value, checkpoint_value
