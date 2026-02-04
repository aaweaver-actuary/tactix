"""Define the Lichess client implementation."""

from __future__ import annotations

import logging
from importlib import import_module

import berserk
from berserk.types.common import PerfType
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from tactix.chess_clients.base_chess_client import (
    BaseChessClient,
    ChessFetchRequest,
    ChessFetchResult,
)
from tactix.chess_clients.chess_game_row import coerce_rows_for_model
from tactix.chess_clients.fetch_helpers import use_fixture_games
from tactix.coerce_perf_type__lichess_client import _coerce_perf_type
from tactix.define_lichess_client_context__lichess_client import LichessClientContext
from tactix.define_lichess_fetch_result__lichess_client import LichessFetchResult
from tactix.define_lichess_game_row__lichess_client import LichessGameRow
from tactix.is_auth_error__lichess_client import _is_auth_error
from tactix.latest_timestamp import latest_timestamp
from tactix.load_fixture_games import FixtureGamesRequest, load_fixture_games
from tactix.pgn_to_game_row__lichess_client import _pgn_to_game_row
from tactix.resolve_perf_value__lichess_client import _resolve_perf_value
from tactix.utils.logger import get_logger

logger = get_logger(__name__)


class LichessClient(BaseChessClient):
    """Client for Lichess API interactions."""

    def __init__(self, context: LichessClientContext) -> None:
        """Initialize the client with Lichess-specific context.

        Args:
            context: Client context containing settings and logger.
        """

        super().__init__(context)

    def fetch_incremental_games(self, request: ChessFetchRequest) -> ChessFetchResult:
        """Fetch Lichess games incrementally.

        Args:
            request: Parameters for the incremental fetch.

        Returns:
            Lichess fetch result with games payload and timestamp metadata.

        Example:
            >>> client.fetch_incremental_games(LichessFetchRequest(since_ms=0))
        """

        games = self._fetch_games(request)
        last_ts = latest_timestamp(games)
        return LichessFetchResult(
            games=games,
            next_cursor=None,
            last_timestamp_ms=last_ts,
        )

    def _fetch_games(self, request: ChessFetchRequest) -> list[dict]:
        """Fetch games from fixtures or the remote API.

        Args:
            request: Request parameters for the fetch.

        Returns:
            List of game rows.
        """

        if use_fixture_games(
            self.settings.lichess.token,
            self.settings.use_fixture_when_no_token,
        ):
            return self._load_fixture_games(request.since_ms, request.until_ms)
        return self._fetch_remote_games(request.since_ms, request.until_ms)

    def _load_fixture_games(self, since_ms: int, until_ms: int | None) -> list[dict]:
        """Load Lichess fixture games.

        Args:
            since_ms: Minimum timestamp for included games.
            until_ms: Optional upper bound timestamp.

        Returns:
            Fixture game rows.
        """

        return load_fixture_games(
            FixtureGamesRequest(
                fixture_path=self.settings.fixture_pgn_path,
                user=self.settings.user,
                source=self.settings.source,
                since_ms=since_ms,
                until_ms=until_ms,
                logger=self.logger,
                coerce_rows=coerce_rows_for_model(LichessGameRow),
            )
        )

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _fetch_remote_games(self, since_ms: int, until_ms: int | None) -> list[dict]:
        """Fetch games from the remote API with retry.

        Args:
            since_ms: Minimum timestamp for included games.
            until_ms: Optional upper bound timestamp.

        Returns:
            Remote game rows.
        """

        return self._fetch_remote_games_with_refresh(since_ms, until_ms)

    def _fetch_remote_games_with_refresh(self, since_ms: int, until_ms: int | None) -> list[dict]:
        """Fetch remote games and refresh token on auth errors.

        Args:
            since_ms: Minimum timestamp for included games.
            until_ms: Optional upper bound timestamp.

        Returns:
            Remote game rows.
        """

        try:
            return self._fetch_remote_games_once(since_ms, until_ms)
        except Exception as exc:
            if self._should_refresh_token(exc):
                self.logger.warning("Refreshing Lichess OAuth token after auth failure")
                lichess_shim = import_module("tactix.lichess_client")
                lichess_shim.refresh_lichess_token(self.settings)
                return self._fetch_remote_games_once(since_ms, until_ms)
            raise

    def _should_refresh_token(self, exc: BaseException) -> bool:
        """Determine if a refresh token should be used.

        Args:
            exc: Exception raised by the API.

        Returns:
            True when a token refresh should be attempted.
        """

        return bool(_is_auth_error(exc) and self.settings.lichess.oauth_refresh_token)

    def _fetch_remote_games_once(self, since_ms: int, until_ms: int | None) -> list[dict]:
        """Fetch games from the remote API once.

        Args:
            since_ms: Minimum timestamp for included games.
            until_ms: Optional upper bound timestamp.

        Returns:
            Remote game rows.
        """

        lichess_shim = import_module("tactix.lichess_client")
        client = lichess_shim.build_client(self.settings)
        perf_type = _coerce_perf_type(_resolve_perf_value(self.settings))
        return self._collect_remote_games(client, since_ms, until_ms, perf_type)

    def _collect_remote_games(
        self,
        client: berserk.Client,
        since_ms: int,
        until_ms: int | None,
        perf_type: PerfType | None,
    ) -> list[dict]:
        """Collect game rows from the API stream.

        Args:
            client: Berserk client instance.
            since_ms: Minimum timestamp for included games.
            until_ms: Optional upper bound timestamp.
            perf_type: Lichess performance filter.

        Returns:
            Remote game rows.
        """

        self.logger.info(
            "Fetching Lichess games for user=%s since=%s", self.settings.user, since_ms
        )
        games: list[dict] = []
        for pgn in client.games.export_by_player(
            self.settings.user,
            since=since_ms or None,
            until=until_ms or None,
            perf_type=perf_type,
            evals=False,
            clocks=True,
            moves=True,
            opening=True,
            max=200,
        ):
            row = _pgn_to_game_row(pgn, self.settings)
            if row:
                games.append(row)
        self.logger.info("Fetched %s PGNs", len(games))
        return games
