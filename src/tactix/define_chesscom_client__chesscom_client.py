"""Define the Chess.com client implementation."""

from __future__ import annotations

# pylint: disable=fixme,broad-exception-caught
import time

import requests

from tactix.build_auth_headers__chesscom_auth import _auth_headers
from tactix.build_cursor__chesscom_cursor import _build_cursor
from tactix.chess_clients.base_chess_client import (
    BaseChessClient,
    ChessFetchRequest,
    ChessFetchResult,
)
from tactix.chess_clients.chess_game_row import (
    ChessGameRow,
    coerce_game_row_dict,
    coerce_rows_for_model,
)
from tactix.chess_clients.fetch_helpers import use_fixture_games
from tactix.define_chesscom_client_context__chesscom_client import ChesscomClientContext
from tactix.errors import RateLimitError
from tactix.extract_game_id import extract_game_id
from tactix.extract_last_timestamp_ms import extract_last_timestamp_ms
from tactix.filter_by_cursor__chesscom_cursor import _filter_by_cursor
from tactix.latest_timestamp import (
    latest_timestamp,
)
from tactix.load_fixture_games import FixtureGamesRequest, load_fixture_games
from tactix.parse_cursor__chesscom_cursor import _parse_cursor
from tactix.parse_retry_after__chesscom_rate_limit import _parse_retry_after
from tactix.resolve_next_page_url__chesscom_pagination import _next_page_url
from tactix.should_stop_archive_fetch__chesscom_archive import _should_stop_archive_fetch
from tactix.utils import Logger

logger = Logger(__name__)

ARCHIVES_URL = "https://api.chess.com/pub/player/{username}/games/archives"
HTTP_STATUS_TOO_MANY_REQUESTS = 429


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

        if use_fixture_games(
            self.settings.chesscom.token,
            self.settings.chesscom_use_fixture_when_no_token,
        ):
            return self._load_fixture_games(request.since_ms)
        return self._fetch_remote_games(request.since_ms, request.full_history)

    def _load_fixture_games(self, since_ms: int) -> list[dict]:
        """Load Chess.com fixture games.

        Args:
            since_ms: Minimum timestamp for included games.

        Returns:
            Fixture game rows.
        """

        return load_fixture_games(
            FixtureGamesRequest(
                fixture_path=self.settings.chesscom_fixture_pgn_path,
                user=self.settings.user,
                source=self.settings.source,
                since_ms=since_ms,
                logger=self.logger,
                missing_message="Chess.com fixture PGN path missing: %s",
                loaded_message="Loaded %s Chess.com fixture PGNs from %s",
                coerce_rows=coerce_rows_for_model(ChessGameRow),
            )
        )

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

        if game.get("time_class") != self.settings.chesscom.time_class:
            return None, 0
        pgn = game.get("pgn")
        if not pgn:
            return None, 0
        last_ts = extract_last_timestamp_ms(pgn)
        game_id = str(game.get("uuid") or extract_game_id(pgn))
        row = self._build_game_row(game_id, pgn, last_ts)
        return coerce_game_row_dict(row, model_cls=ChessGameRow), last_ts

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

        max_retries = max(self.settings.chesscom.max_retries, 0)
        base_backoff = max(self.settings.chesscom.retry_backoff_ms, 0) / 1000.0
        attempt = 0
        while True:
            response = requests.get(
                url,
                headers=_auth_headers(self.settings.chesscom.token),
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
