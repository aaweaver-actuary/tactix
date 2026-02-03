from __future__ import annotations

import json

from tactix.utils import funclogger, hash


@funclogger
def _analysis_signature(game_ids: list[str], positions_count: int, source: str) -> str:
    """
    Generates a unique SHA-256 hash signature for a given set of game analysis parameters.

    Parameters
    ----------
    game_ids : list[str]
        A list of game IDs being analyzed.
    positions_count : int
        The total number of positions analyzed across the games.
    source : str
        The source of the analysis request.

    Returns
    -------
    str
        A SHA-256 hash signature representing the analysis parameters.
    """
    payload = {
        "game_ids": game_ids,
        "positions_count": positions_count,
        "source": source,
    }
    serialized = json.dumps(payload, sort_keys=True)
    return hash(serialized)
