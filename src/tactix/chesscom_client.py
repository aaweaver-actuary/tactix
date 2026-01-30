from __future__ import annotations

import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import cast
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests

from tactix.chess_clients.base_chess_client import (
    BaseChessClient,
    BaseChessClientContext,
    ChessFetchRequest,
    ChessFetchResult,
)
from tactix.chess_clients.chess_game_row import ChessGameRow
from tactix.chess_clients.fixture_helpers import (
    load_fixture_games_for_client,
    should_use_fixture_games,
)
from tactix.config import Settings
from tactix.errors import RateLimitError
from tactix.pgn_utils import (
    extract_game_id,
    extract_last_timestamp_ms,
    latest_timestamp,
)
from tactix.utils import Logger, to_int

logger = Logger(__name__)

ARCHIVES_URL = "https://api.chess.com/pub/player/{username}/games/archives"
HTTP_STATUS_TOO_MANY_REQUESTS = 429

__all__ = [
    "ARCHIVES_URL",
    "ChesscomClient",
    "ChesscomClientContext",
    "_auth_headers",
    "_build_cursor",
    "_fetch_archive_pages",
    "_fetch_remote_games",
    "_filter_by_cursor",
    "_get_with_backoff",
    "_load_fixture_games",
    "_next_page_url",
    "_parse_cursor",
    "_parse_retry_after",
    "fetch_incremental_games",
    "read_cursor",
    "to_int",
    "write_cursor",
]


@dataclass(slots=True)
class ChesscomClientContext(BaseChessClientContext):
    """Context for Chess.com API interactions."""


class ChesscomClient(BaseChessClient):
    """Client for Chess.com API interactions."""

    def __init__(self, context: ChesscomClientContext) -> None:
        """Initialize the client with Chess.com-specific context.

        Args:
            context: Client context containing settings and logger.
        """

        super().__init__(context)

    def fetch_incremental_games(self, request: ChessFetchRequest) -> ChessFetchResult:
        """Fetch Chess.com games incrementally.

        Args:
            request: Parameters for the incremental fetch.

        Returns:
            Chess.com fetch result with games and cursor metadata.

        Example:
            >>> client.fetch_incremental_games(ChessFetchRequest(cursor=None))
        """

        raw_games = self._fetch_raw_games(request)
        games = self._attach_cursors(_filter_by_cursor(raw_games, request.cursor))
        last_ts = self._resolve_last_timestamp(games, request.cursor)
        next_cursor = self._resolve_next_cursor(games, request.cursor)
        self._log_fetch_summary(request.cursor, next_cursor, len(games))
        return ChessFetchResult(
            games=games,
            next_cursor=next_cursor,
            last_timestamp_ms=last_ts,
        )

    def _fetch_raw_games(self, request: ChessFetchRequest) -> list[dict]:
        """Fetch raw games from fixtures or the remote API.

        Args:
            request: Parameters for the incremental fetch.

        Returns:
            List of raw Chess.com game rows.
        """

        if self._use_fixture_games():
            return self._load_fixture_games(request.since_ms)
        return self._fetch_remote_games(request.since_ms, request.full_history)

    def _use_fixture_games(self) -> bool:
        """Decide if fixture data should be used.

        Returns:
            True when fixtures should be used, otherwise False.
        """

        return should_use_fixture_games(
            self.settings.chesscom_token,
            self.settings.chesscom_use_fixture_when_no_token,
        )

    def _load_fixture_games(self, since_ms: int) -> list[dict]:
        """Load Chess.com fixture games.

        Args:
            since_ms: Minimum timestamp for included games.

        Returns:
            Fixture game rows.
        """

        games = load_fixture_games_for_client(
            fixture_path=self.settings.chesscom_fixture_pgn_path,
            user=self.settings.user,
            source=self.settings.source,
            since_ms=since_ms,
            logger=self.logger,
            missing_message="Chess.com fixture PGN path missing: %s",
            loaded_message="Loaded %s Chess.com fixture PGNs from %s",
        )
        return self._coerce_games(games)

    def _fetch_remote_games(self, since_ms: int, full_history: bool) -> list[dict]:
        """Fetch Chess.com games from the remote API.

        Args:
            since_ms: Minimum timestamp for included games.
            full_history: Whether to fetch full history.

        Returns:
            Remote game rows.
        """

        archives = self._fetch_archive_index()
        if archives is None:
            return self._load_fixture_games(since_ms)
        if not archives:
            return []
        archives_to_fetch = archives if full_history else archives[-6:]
        return self._collect_archives(archives_to_fetch, since_ms)

    def _fetch_archive_index(self) -> list[str] | None:
        """Fetch the archive list for the configured user.

        Returns:
            List of archive URLs.
        """

        url = ARCHIVES_URL.format(username=self.settings.user)
        try:
            response = self._get_with_backoff(url, timeout=15)
        except Exception as exc:
            self.logger.warning("Falling back to fixtures; archive fetch failed: %s", exc)
            return None
        archives = response.json().get("archives", [])
        if not archives:
            self.logger.info("No archives returned for %s", self.settings.user)
        return list(archives)

    def _collect_archives(self, archives: list[str], since_ms: int) -> list[dict]:
        """Collect games across multiple archives.

        Args:
            archives: Archive URLs to fetch.
            since_ms: Minimum timestamp for included games.

        Returns:
            Aggregated Chess.com game rows.
        """

        games: list[dict] = []
        for archive_url in reversed(archives):
            archive_games = self._safe_fetch_archive(archive_url)
            if not archive_games:
                continue
            if self._append_archive_games(games, archive_games, since_ms):
                break
        self.logger.info("Fetched %s Chess.com PGNs", len(games))
        return games

    def _safe_fetch_archive(self, archive_url: str) -> list[dict]:
        """Fetch a single archive page with error handling.

        Args:
            archive_url: Archive endpoint URL.

        Returns:
            List of raw game dictionaries.
        """

        try:
            return self._fetch_archive_pages(archive_url)
        except Exception as exc:
            self.logger.warning("Failed to fetch archive %s: %s", archive_url, exc)
            return []

    def _append_archive_games(
        self, games: list[dict], archive_games: list[dict], since_ms: int
    ) -> bool:
        """Append archive games to the accumulator.

        Args:
            games: Accumulator list for games.
            archive_games: Raw games from the archive.
            since_ms: Minimum timestamp for included games.

        Returns:
            True if the caller should stop fetching older archives.
        """

        archive_max_ts = 0
        seen_game_ids: set[str] = set()
        for game in archive_games:
            row, last_ts = self._coerce_game(game)
            if row is None:
                continue
            archive_max_ts = max(archive_max_ts, last_ts)
            if self._should_skip_game(row, last_ts, since_ms, seen_game_ids):
                continue
            seen_game_ids.add(str(row.get("game_id", "")))
            games.append(row)
        return _should_stop_archive_fetch(since_ms, archive_max_ts)

    def _coerce_game(self, game: dict) -> tuple[dict | None, int]:
        """Coerce a raw API game dict into a model.

        Args:
            game: Raw game dictionary.

        Returns:
            Tuple of model and last timestamp.
        """

        if game.get("time_class") != self.settings.chesscom_time_class:
            return None, 0
        pgn = game.get("pgn")
        if not pgn:
            return None, 0
        last_ts = extract_last_timestamp_ms(pgn)
        game_id = str(game.get("uuid") or extract_game_id(pgn))
        row = self._build_game_row(game_id, pgn, last_ts)
        validated = ChessGameRow.model_validate(row.model_dump())
        return validated.model_dump(), last_ts

    # TODO: Pass ChessGame instance instead of raw dict
    def _should_skip_game(
        self,
        row: dict,
        last_ts: int,
        since_ms: int,
        seen_game_ids: set[str],
    ) -> bool:
        """Determine whether a game should be skipped.

        Args:
            row: Normalized game row.
            last_ts: Game timestamp.
            since_ms: Minimum timestamp filter.
            seen_game_ids: Previously seen game identifiers.

        Returns:
            True if the game should be skipped.
        """

        if since_ms and last_ts <= since_ms:
            return True
        return str(row.get("game_id", "")) in seen_game_ids

    def _fetch_archive_pages(self, archive_url: str) -> list[dict]:
        """Fetch all pages for a given archive URL.

        Args:
            archive_url: Archive endpoint URL.

        Returns:
            List of raw game dictionaries.
        """

        games: list[dict] = []
        next_url: str | None = archive_url
        seen_urls: set[str] = set()
        while next_url:
            if next_url in seen_urls:
                self.logger.warning("Pagination loop detected for %s", archive_url)
                break
            seen_urls.add(next_url)
            payload = self._get_with_backoff(next_url, timeout=20).json()
            games.extend(payload.get("games", []))
            next_url = _next_page_url(payload, next_url)
        return games

    def _get_with_backoff(self, url: str, timeout: int) -> requests.Response:
        """Fetch a URL with exponential backoff on 429 responses.

        Args:
            url: URL to request.
            timeout: Timeout in seconds.

        Returns:
            Response object.

        Raises:
            RateLimitError: When retries are exhausted.
        """

        max_retries = max(self.settings.chesscom_max_retries, 0)
        base_backoff = max(self.settings.chesscom_retry_backoff_ms, 0) / 1000.0
        attempt = 0
        while True:
            response = requests.get(
                url,
                headers=_auth_headers(self.settings.chesscom_token),
                timeout=timeout,
            )
            if response.status_code != HTTP_STATUS_TOO_MANY_REQUESTS:
                response.raise_for_status()
                return response
            attempt = self._handle_rate_limit(response, attempt, max_retries, base_backoff)

    def _handle_rate_limit(
        self,
        response: requests.Response,
        attempt: int,
        max_retries: int,
        base_backoff: float,
    ) -> int:
        """Handle a rate-limited response.

        Args:
            response: HTTP response.
            attempt: Current attempt count.
            max_retries: Maximum retry count.
            base_backoff: Base backoff in seconds.

        Returns:
            Next attempt count.
        """

        retry_after = _parse_retry_after(response.headers.get("Retry-After"))
        if attempt >= max_retries:
            message = "Chess.com rate limit exceeded"
            raise RateLimitError(message, response=response)
        wait_seconds = max(base_backoff * (2**attempt), retry_after or 0.0)
        self.logger.warning(
            "Chess.com rate limited (429). Retrying in %.2fs (attempt %s/%s).",
            wait_seconds,
            attempt + 1,
            max_retries,
        )
        if wait_seconds:
            time.sleep(wait_seconds)
        return attempt + 1

    @staticmethod
    def _attach_cursors(games: list[dict]) -> list[dict]:
        """Attach cursor values to each game.

        Args:
            games: Games to decorate with cursors.

        Returns:
            Games with cursor values populated.
        """

        for game in games:
            game["cursor"] = _build_cursor(
                int(game.get("last_timestamp_ms", 0)), str(game.get("game_id", ""))
            )
        return games

    @staticmethod
    def _resolve_last_timestamp(games: list[dict], cursor: str | None) -> int:
        """Resolve the latest timestamp for the response.

        Args:
            games: Fetched games.
            cursor: Cursor token to fall back on.

        Returns:
            Latest timestamp value.
        """

        if games:
            return latest_timestamp(games)
        return _parse_cursor(cursor)[0]

    @staticmethod
    def _resolve_next_cursor(games: list[dict], cursor: str | None) -> str | None:
        """Resolve the next cursor for pagination.

        Args:
            games: Fetched games.
            cursor: Cursor token to fall back on.

        Returns:
            Next cursor value.
        """

        if games:
            newest = max(games, key=lambda g: int(g.get("last_timestamp_ms", 0)))
            return _build_cursor(
                int(newest.get("last_timestamp_ms", 0)), str(newest.get("game_id", ""))
            )
        return cursor if cursor else None

    def _log_fetch_summary(self, cursor: str | None, next_cursor: str | None, count: int) -> None:
        """Log a summary for a fetch.

        Args:
            cursor: Incoming cursor.
            next_cursor: Outgoing cursor.
            count: Number of games fetched.
        """

        self.logger.info(
            "Fetched %s Chess.com PGNs with cursor=%s next_cursor=%s",
            count,
            cursor,
            next_cursor,
        )

    @staticmethod
    def _coerce_games(rows: Iterable[dict]) -> list[dict]:
        """Coerce raw rows into validated models.

        Args:
            rows: Iterable of raw row dictionaries.

        Returns:
            Validated game rows.
        """

        return [ChessGameRow.model_validate(row).model_dump() for row in rows]


def _should_stop_archive_fetch(since_ms: int, archive_max_ts: int) -> bool:
    return bool(since_ms and archive_max_ts and archive_max_ts <= since_ms)


def _auth_headers(token: str | None) -> dict[str, str]:
    """Build authorization headers.

    Args:
        token: API token if available.

    Returns:
        Headers dict for the request.
    """

    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _parse_retry_after(value: str | None) -> float | None:
    """Parse Retry-After header values.

    Args:
        value: Retry-After header value.

    Returns:
        Number of seconds to wait, or None.
    """

    if not value:
        return None
    seconds = _parse_retry_after_seconds(value)
    if seconds is not None:
        return seconds
    return _parse_retry_after_date(value)


def _parse_retry_after_seconds(value: str) -> float | None:
    """Parse Retry-After as a numeric duration.

    Args:
        value: Retry-After header value.

    Returns:
        Parsed seconds or None.
    """

    try:
        seconds = float(value)
    except ValueError:
        return None
    return max(seconds, 0.0)


def _parse_retry_after_date(value: str) -> float | None:
    """Parse Retry-After as an HTTP date.

    Args:
        value: Retry-After header value.

    Returns:
        Parsed seconds or None.
    """

    try:
        dt = parsedate_to_datetime(value)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    delta = (dt - datetime.now(UTC)).total_seconds()
    return max(delta, 0.0)


def _get_with_backoff(settings: Settings, url: str, timeout: int) -> requests.Response:
    """Fetch a URL with exponential backoff on 429 responses.

    Args:
        settings: Settings for the request.
        url: URL to request.
        timeout: Timeout in seconds.

    Returns:
        Response object.
    """

    context = ChesscomClientContext(settings=settings, logger=logger)
    return ChesscomClient(context)._get_with_backoff(url, timeout)


def _parse_cursor(cursor: str | None) -> tuple[int, str]:
    """Parse a cursor token into timestamp and id.

    Args:
        cursor: Cursor token.

    Returns:
        Tuple of timestamp and game id.
    """

    if not cursor:
        return 0, ""
    if ":" in cursor:
        prefix, suffix = cursor.split(":", 1)
        try:
            return int(prefix), suffix
        except ValueError:
            return 0, cursor
    if cursor.isdigit():
        return int(cursor), ""
    return 0, cursor


def _build_cursor(last_ts: int, game_id: str) -> str:
    """Build a cursor token.

    Args:
        last_ts: Last timestamp in milliseconds.
        game_id: Game identifier.

    Returns:
        Cursor token.
    """

    return f"{last_ts}:{game_id}"


def read_cursor(path: Path) -> str | None:
    """Read a cursor token from disk.

    Args:
        path: Cursor path.

    Returns:
        Cursor token or None.
    """

    try:
        raw = path.read_text().strip()
    except FileNotFoundError:
        return None
    return raw or None


def write_cursor(path: Path, cursor: str | None) -> None:
    """Write a cursor token to disk.

    Args:
        path: Cursor file path.
        cursor: Cursor token to persist.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    if cursor is None:
        path.write_text("")
        return
    path.write_text(cursor)


def _load_fixture_games(settings: Settings, since_ms: int) -> list[dict]:
    """Load Chess.com fixture games.

    Args:
        settings: Settings for fixtures.
        since_ms: Minimum timestamp for included games.

    Returns:
        Raw fixture games.
    """

    client = ChesscomClient(ChesscomClientContext(settings=settings, logger=logger))
    return client._load_fixture_games(since_ms)


def _next_page_url(data: dict, current_url: str) -> str | None:
    """Resolve the next page URL from a response payload.

    Args:
        data: Response payload.
        current_url: Current URL used for pagination.

    Returns:
        Next page URL if available.
    """

    candidate = _next_page_candidate(data)
    return candidate or _page_from_numbers(data, current_url)


def _next_page_candidate(data: dict) -> str | None:
    for key in ("next_page", "next", "next_url", "nextPage"):
        href = _extract_candidate_href(data.get(key))
        if href:
            return href
    return None


def _extract_candidate_href(candidate: object) -> str | None:
    if isinstance(candidate, str):
        return _non_empty_str(candidate)
    if isinstance(candidate, Mapping):
        candidate_map = cast(Mapping[str, object], candidate)
        return _first_string(candidate_map, ("href", "url"))
    return None


def _non_empty_str(value: str) -> str | None:
    return value if value else None


def _first_string(mapping: Mapping[str, object], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _page_from_numbers(data: dict, current_url: str) -> str | None:
    """Compute a next page URL from numeric pagination fields.

    Args:
        data: Response payload.
        current_url: Current URL used for pagination.

    Returns:
        Next page URL if determinable.
    """

    page_info = _pagination_values(data)
    if page_info is None:
        return None
    page, total_pages = page_info
    if page >= total_pages:
        return None
    return _page_url_for(current_url, page + 1)


def _pagination_values(data: Mapping[str, object]) -> tuple[int, int] | None:
    page = to_int(data.get("page") or data.get("current_page"))
    total_pages = to_int(data.get("total_pages") or data.get("totalPages"))
    if page is None or total_pages is None:
        return None
    return page, total_pages


def _page_url_for(current_url: str, page: int) -> str:
    parsed = urlparse(current_url)
    query = parse_qs(parsed.query)
    query["page"] = [str(page)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def _fetch_archive_pages(settings: Settings, archive_url: str) -> list[dict]:
    """Fetch all pages for a given archive URL.

    Args:
        settings: Settings for the request.
        archive_url: Archive endpoint URL.

    Returns:
        List of raw game dictionaries.
    """

    context = ChesscomClientContext(settings=settings, logger=logger)
    return ChesscomClient(context)._fetch_archive_pages(archive_url)


def _fetch_remote_games(
    settings: Settings, since_ms: int, *, full_history: bool = False
) -> list[dict]:
    """Fetch Chess.com games from the remote API.

    Args:
        settings: Settings for the request.
        since_ms: Minimum timestamp for included games.
        full_history: Whether to fetch full history.

    Returns:
        Raw game rows.
    """

    context = ChesscomClientContext(settings=settings, logger=logger)
    return ChesscomClient(context)._fetch_remote_games(since_ms, full_history)


def _filter_by_cursor(rows: list[dict], cursor: str | None) -> list[dict]:
    """Filter rows using a cursor token.

    Args:
        rows: Candidate rows to filter.
        cursor: Cursor token to apply.

    Returns:
        Filtered list of rows.
    """

    since_ts, since_game = _parse_cursor(cursor)
    ordered = sorted(rows, key=lambda g: int(g.get("last_timestamp_ms", 0)))
    return [game for game in ordered if _cursor_allows_game(game, since_ts, since_game)]


def _cursor_allows_game(game: dict, since_ts: int, since_game: str) -> bool:
    last_ts = int(game.get("last_timestamp_ms", 0))
    return (
        (not since_ts)
        or (last_ts > since_ts)
        or (last_ts == since_ts and str(game.get("game_id", "")) > since_game)
    )


def fetch_incremental_games(
    settings: Settings, cursor: str | None, *, full_history: bool = False
) -> ChessFetchResult:
    """Fetch Chess.com games incrementally.

    Args:
        settings: Settings for the request.
        cursor: Cursor token.
        full_history: Whether to fetch full history.

    Returns:
        Chess.com fetch result containing games and cursor metadata.
    """

    context = ChesscomClientContext(settings=settings, logger=logger)
    request = ChessFetchRequest(cursor=cursor, full_history=full_history)
    return cast(ChessFetchResult, ChesscomClient(context).fetch_incremental_games(request))
