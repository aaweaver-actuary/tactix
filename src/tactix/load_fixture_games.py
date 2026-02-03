import logging
from collections.abc import Callable, Iterable
from pathlib import Path

from tactix._coerce_fixture_rows import _coerce_fixture_rows
from tactix._filter_fixture_games import _filter_fixture_games
from tactix._resolve_fixture_message import _resolve_fixture_message
from tactix.split_pgn_chunks import split_pgn_chunks
from tactix.utils import Logger


def load_fixture_games(
    fixture_path: Path,
    user: str,
    source: str,
    since_ms: int,
    *,
    until_ms: int | None = None,
    logger: logging.Logger | None = None,
    missing_message: str | None = None,
    loaded_message: str | None = None,
    coerce_rows: Callable[[Iterable[dict[str, object]]], list[dict]] | None = None,
) -> list[dict[str, object]]:
    """Load fixture PGNs from disk and apply since/until timestamp filters."""
    active_logger = logger or Logger(__name__)
    resolved_missing_message = _resolve_fixture_message(
        missing_message,
        "Fixture PGN path missing: %s",
    )
    resolved_loaded_message = _resolve_fixture_message(
        loaded_message,
        "Loaded %s fixture PGNs from %s",
    )
    if not fixture_path.exists():
        active_logger.warning(resolved_missing_message, fixture_path)
        return []
    chunks = split_pgn_chunks(fixture_path.read_text())
    games = _filter_fixture_games(chunks, user, source, since_ms, until_ms)
    active_logger.info(resolved_loaded_message, len(games), fixture_path)
    return _coerce_fixture_rows(games, coerce_rows)
