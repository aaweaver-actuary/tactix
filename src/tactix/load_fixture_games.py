"""Load fixture games from disk for testing or demos."""

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from tactix._coerce_fixture_rows import _coerce_fixture_rows
from tactix._filter_fixture_games import _filter_fixture_games
from tactix._resolve_fixture_message import _resolve_fixture_message
from tactix.legacy_args import apply_legacy_args, apply_legacy_kwargs, init_legacy_values
from tactix.split_pgn_chunks import split_pgn_chunks
from tactix.utils import Logger


@dataclass(frozen=True)
class FixtureGamesRequest:  # pylint: disable=too-many-instance-attributes
    """Inputs for loading fixture games."""

    fixture_path: Path
    user: str
    source: str
    since_ms: int
    until_ms: int | None = None
    logger: logging.Logger | None = None
    missing_message: str | None = None
    loaded_message: str | None = None
    coerce_rows: Callable[[Iterable[dict[str, object]]], list[dict]] | None = None


def _collect_fixture_values(
    args: tuple[object, ...],
    legacy: dict[str, object],
) -> dict[str, object]:
    ordered_keys = (
        "user",
        "source",
        "since_ms",
        "until_ms",
        "logger",
        "missing_message",
        "loaded_message",
        "coerce_rows",
    )
    values = init_legacy_values(ordered_keys)
    apply_legacy_kwargs(values, ordered_keys, legacy)
    apply_legacy_args(values, ordered_keys, args)
    return values


def _build_fixture_request(
    request: Path | str,
    values: dict[str, object],
) -> FixtureGamesRequest:
    if values["user"] is None or values["source"] is None or values["since_ms"] is None:
        raise TypeError("fixture_path, user, source, and since_ms are required")
    user = cast(str, values["user"])
    source = cast(str, values["source"])
    since_ms = cast(int, values["since_ms"])
    until_ms = cast(int | None, values["until_ms"])
    logger = cast(logging.Logger | None, values["logger"])
    missing_message = cast(str | None, values["missing_message"])
    loaded_message = cast(str | None, values["loaded_message"])
    coerce_rows = cast(
        Callable[[Iterable[dict[str, object]]], list[dict]] | None,
        values["coerce_rows"],
    )
    return FixtureGamesRequest(
        fixture_path=Path(request),
        user=user,
        source=source,
        since_ms=since_ms,
        until_ms=until_ms,
        logger=logger,
        missing_message=missing_message,
        loaded_message=loaded_message,
        coerce_rows=coerce_rows,
    )


def load_fixture_games(
    request: FixtureGamesRequest | Path | str,
    *args: object,
    **legacy: object,
) -> list[dict[str, object]]:
    """Load fixture PGNs from disk and apply since/until timestamp filters."""
    if isinstance(request, FixtureGamesRequest):
        resolved_request = request
    else:
        values = _collect_fixture_values(args, legacy)
        resolved_request = _build_fixture_request(request, values)
    active_logger = resolved_request.logger or Logger(__name__)
    resolved_missing_message = _resolve_fixture_message(
        resolved_request.missing_message,
        "Fixture PGN path missing: %s",
    )
    resolved_loaded_message = _resolve_fixture_message(
        resolved_request.loaded_message,
        "Loaded %s fixture PGNs from %s",
    )
    if not resolved_request.fixture_path.exists():
        active_logger.warning(resolved_missing_message, resolved_request.fixture_path)
        return []
    chunks = split_pgn_chunks(resolved_request.fixture_path.read_text(encoding="utf-8"))
    games = _filter_fixture_games(
        chunks,
        resolved_request.user,
        resolved_request.source,
        resolved_request.since_ms,
        resolved_request.until_ms,
    )
    active_logger.info(
        resolved_loaded_message,
        len(games),
        resolved_request.fixture_path,
    )
    return _coerce_fixture_rows(games, resolved_request.coerce_rows)
