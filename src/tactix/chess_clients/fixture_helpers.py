from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from tactix.pgn_utils import load_fixture_games


def should_use_fixture_games(token: str | None, use_fixture_when_no_token: bool) -> bool:
    return bool(not token and use_fixture_when_no_token)


def load_fixture_games_for_client(
    *,
    fixture_path: Path,
    user: str,
    source: str,
    since_ms: int,
    until_ms: int | None = None,
    logger: logging.Logger | None = None,
    missing_message: str | None = None,
    loaded_message: str | None = None,
) -> list[dict[str, Any]]:
    resolved_missing_message = (
        missing_message if missing_message is not None else "Fixture PGN path missing: %s"
    )
    resolved_loaded_message = (
        loaded_message if loaded_message is not None else "Loaded %s fixture PGNs from %s"
    )
    return load_fixture_games(
        fixture_path,
        user,
        source,
        since_ms,
        until_ms=until_ms,
        logger=logger,
        missing_message=resolved_missing_message,
        loaded_message=resolved_loaded_message,
    )
