"""Lichess client implementation and helpers (adapter layer)."""

# pylint: disable=protected-access,undefined-all-variable

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import berserk
import requests
from berserk.types.common import PerfType
from pydantic import Field
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from tactix.chess_clients.base_chess_client import (
    BaseChessClient,
    BaseChessClientContext,
    ChessFetchRequest,
    ChessFetchResult,
)
from tactix.chess_clients.chess_game_row import (
    ChessGameRow,
    build_game_row_dict,
    coerce_rows_for_model,
)
from tactix.chess_clients.fetch_helpers import run_incremental_fetch, use_fixture_games
from tactix.chess_clients.GameRowInputs import GameRowInputs
from tactix.config import Settings
from tactix.extract_game_id import extract_game_id
from tactix.extract_last_timestamp_ms import extract_last_timestamp_ms
from tactix.latest_timestamp import latest_timestamp
from tactix.load_fixture_games import FixtureGamesRequest, load_fixture_games
from tactix.read_optional_text__filesystem import _read_optional_text
from tactix.utils.logger import Logger

logger = Logger(__name__)

_PERF_TYPES: set[str] = {
    "ultraBullet",
    "bullet",
    "blitz",
    "rapid",
    "classical",
    "correspondence",
    "chess960",
    "kingOfTheHill",
    "threeCheck",
    "antichess",
    "atomic",
    "horde",
    "racingKings",
    "crazyhouse",
    "fromPosition",
}


def _coerce_perf_type(value: str | None) -> PerfType | None:
    """Coerce a string to a Lichess perf type.

    Args:
        value: Perf type string.

    Returns:
        Perf type if valid, otherwise None.
    """

    if not value:
        return None
    if value in _PERF_TYPES:
        return cast(PerfType, value)
    return None


def _coerce_pgn_text(pgn: object) -> str:
    """Coerce PGN payloads to text.

    Args:
        pgn: PGN payload from the API.

    Returns:
        PGN text.
    """

    if isinstance(pgn, (bytes, bytearray)):
        return pgn.decode("utf-8", errors="replace")
    return str(pgn)


def _extract_status_code(exc: BaseException) -> int | None:
    """Extract status codes from Lichess API exceptions.

    Args:
        exc: Exception raised by the API.

    Returns:
        Status code if available.
    """

    for attr in ("status", "status_code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    return status_code if isinstance(status_code, int) else None


def _is_auth_error(exc: BaseException) -> bool:
    """Check whether an exception represents an auth error.

    Args:
        exc: Exception raised by the API.

    Returns:
        True for auth errors, otherwise False.
    """

    status_code = _extract_status_code(exc)
    return status_code in {401, 403}


def _resolve_perf_value(settings: Settings) -> str:
    """Resolve the perf filter value for a Lichess request.

    Args:
        settings: Settings for the request.

    Returns:
        Perf value string.
    """

    return settings.lichess_profile or settings.rapid_perf


def _parse_cached_payload(raw: str) -> dict[str, object] | None:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _parse_cached_token(raw: str) -> str | None:
    """Return the access token from cached JSON payloads."""

    payload = _parse_cached_payload(raw)
    if payload is None:
        return raw
    token = payload.get("access_token")
    return str(token) if token else None


def _read_cached_token_text(path: Path) -> str | None:
    """Return cached token text if present."""

    return _read_optional_text(path)


def _read_cached_token(path: Path) -> str | None:
    """Read a cached OAuth token from disk.

    Args:
        path: Token cache path.

    Returns:
        Cached token string if available.
    """

    raw = _read_cached_token_text(path)
    if raw is None:
        return None
    return _parse_cached_token(raw)


def _resolve_access_token(settings: Settings) -> str:
    """Resolve the active access token.

    Args:
        settings: Settings for the request.

    Returns:
        Access token string (empty if missing).
    """

    if settings.lichess.token:
        return settings.lichess.token
    cached = _read_cached_token(settings.lichess_token_cache_path)
    return cached or ""


def _write_cached_token(path: Path, token: str) -> None:
    """Write a cached OAuth token to disk.

    Args:
        path: Token cache path.
        token: Token value to persist.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "access_token": token,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
    )
    try:
        os.chmod(path, 0o600)
    except OSError:
        logger.warning("Unable to set permissions on token cache: %s", path)


class LichessTokenError(ValueError):
    """Raised when Lichess OAuth token refresh fails."""


def _refresh_lichess_token(settings: Settings) -> str:
    """Refresh the OAuth token using the configured refresh token.

    Args:
        settings: Settings for the request.

    Returns:
        Newly refreshed access token.

    Raises:
        LichessTokenError: When refresh configuration or response is invalid.
    """

    refresh_token, client_id, client_secret = (
        settings.lichess.oauth_refresh_token,
        settings.lichess.oauth_client_id,
        settings.lichess.oauth_client_secret,
    )
    token_url = settings.lichess.oauth_token_url
    if not all([refresh_token, client_id, client_secret]):
        raise LichessTokenError("Missing Lichess OAuth refresh token configuration")
    response = requests.post(
        token_url,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=15,
    )
    response.raise_for_status()
    access_token = response.json().get("access_token")
    if not access_token:
        raise LichessTokenError("Missing access_token in Lichess OAuth response")
    settings.lichess.token = access_token
    _write_cached_token(settings.lichess_token_cache_path, access_token)
    return access_token


def read_checkpoint(path: Path) -> int:
    """Read a Lichess checkpoint value from disk.

    Args:
        path: Checkpoint path.

    Returns:
        Checkpoint timestamp in milliseconds.
    """

    try:
        return int(path.read_text().strip())
    except FileNotFoundError:
        return 0
    except ValueError:
        logger.warning("Invalid checkpoint file, resetting to 0: %s", path)
        return 0


def write_checkpoint(path: Path, since_ms: int) -> None:
    """Write a Lichess checkpoint value to disk.

    Args:
        path: Checkpoint path.
        since_ms: Timestamp value to persist.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(since_ms))


def _pgn_to_game_row(pgn: object, settings: Settings) -> dict | None:
    """Convert a PGN payload into a game row.

    Args:
        pgn: PGN payload from the API.
        settings: Settings for the request.

    Returns:
        Game row dictionary or None when empty.
    """

    if pgn is None:
        return None
    pgn_text = _coerce_pgn_text(pgn)
    game_id = extract_game_id(pgn_text)
    last_ts = extract_last_timestamp_ms(pgn_text)
    return build_game_row_dict(
        GameRowInputs(
            game_id=game_id,
            pgn=pgn_text,
            last_timestamp_ms=last_ts,
            user=settings.user,
            source=settings.source,
            fetched_at=datetime.now(UTC),
            model_cls=LichessGameRow,
        )
    )


def build_client(settings: Settings) -> berserk.Client:
    """Build a Berserk client for the Lichess API.

    Args:
        settings: Settings for the request.

    Returns:
        Berserk client instance.
    """

    token = _resolve_access_token(settings)
    session = berserk.TokenSession(token)
    return berserk.Client(session=session)


@dataclass(slots=True)
class LichessClientContext(BaseChessClientContext):
    """Context for Lichess API interactions."""


class LichessFetchRequest(ChessFetchRequest):
    """Request parameters for Lichess incremental fetches."""


class LichessFetchResult(ChessFetchResult):
    """Response payload for Lichess incremental fetches."""

    games: list[dict] = Field(default_factory=list)


class LichessGameRow(ChessGameRow):
    """Lichess game row model."""


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
                refresh_lichess_token(self.settings)
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

        client = build_client(self.settings)
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

    context = LichessClientContext(settings=settings, logger=logger)
    return LichessClient(context)._fetch_remote_games_once(since_ms, until_ms)


def _fetch_remote_games(
    settings: Settings, since_ms: int, until_ms: int | None = None
) -> list[dict]:
    """Fetch games from the remote API with retry.

    Args:
        settings: Settings for the request.
        since_ms: Minimum timestamp for included games.
        until_ms: Optional upper bound timestamp.

    Returns:
        Remote game rows.
    """

    context = LichessClientContext(settings=settings, logger=logger)
    return LichessClient(context)._fetch_remote_games(since_ms, until_ms)


def fetch_incremental_games(
    settings: Settings, since_ms: int, until_ms: int | None = None
) -> list[dict]:
    """Fetch Lichess games incrementally.

    Args:
        settings: Settings for the request.
        since_ms: Minimum timestamp for included games.
        until_ms: Optional upper bound timestamp.

    Returns:
        List of game rows.
    """

    context = LichessClientContext(settings=settings, logger=logger)
    request = LichessFetchRequest(since_ms=since_ms, until_ms=until_ms)
    return run_incremental_fetch(
        build_client=lambda: LichessClient(context),
        request=request,
    ).games


def refresh_lichess_token(settings: Settings) -> None:
    """Refresh the cached Lichess OAuth token."""

    _refresh_lichess_token(settings)
