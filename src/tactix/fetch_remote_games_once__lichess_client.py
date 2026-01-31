from __future__ import annotations

from tactix.config import Settings


def _fetch_remote_games_once(
    settings: Settings, since_ms: int, until_ms: int | None = None
) -> list[dict]:
    """Fetch games from the remote API once.

    Args:
        settings: Settings for the request.
        since_ms: Minimum timestamp for included games.
        until_ms: Optional upper bound timestamp.

    Returns:
        Remote game rows.
    """

    from tactix.chess_clients import game_fetching  # noqa: PLC0415

    return game_fetching._fetch_remote_games_once(settings, since_ms, until_ms)
