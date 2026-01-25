from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, TypedDict, cast

import berserk
import requests
from berserk.types.common import PerfType
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from tactix.config import Settings
from tactix.logging_utils import get_logger
from tactix.pgn_utils import (
    extract_game_id,
    extract_last_timestamp_ms,
    latest_timestamp,
    split_pgn_chunks,
)

logger = get_logger(__name__)

__all__ = [
    "build_client",
    "fetch_incremental_games",
    "latest_timestamp",
    "read_checkpoint",
    "write_checkpoint",
]


_PERF_TYPES: set[str] = {
    "ultraBullet",
    "bullet",
    "blitz",
    "rapid",
    "classical",
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
    if not value:
        return None
    if value in _PERF_TYPES:
        return cast(PerfType, value)
    return None


class LichessGameRow(TypedDict):
    game_id: str
    user: str
    source: str
    fetched_at: datetime
    pgn: str
    last_timestamp_ms: int


def _load_fixture_games(
    settings: Settings, since_ms: int, until_ms: int | None = None
) -> List[LichessGameRow]:
    path = settings.fixture_pgn_path
    if not path.exists():
        logger.warning("Fixture PGN path missing: %s", path)
        return []

    chunks = split_pgn_chunks(path.read_text())
    games: List[LichessGameRow] = []
    for raw in chunks:
        last_ts = extract_last_timestamp_ms(raw)
        if since_ms and last_ts <= since_ms:
            continue
        if until_ms is not None and last_ts >= until_ms:
            continue
        games.append(
            {
                "game_id": extract_game_id(raw),
                "user": settings.user,
                "source": settings.source,
                "fetched_at": datetime.now(timezone.utc),
                "pgn": raw,
                "last_timestamp_ms": last_ts,
            }
        )

    logger.info("Loaded %s fixture PGNs from %s", len(games), path)
    return games


def read_checkpoint(path: Path) -> int:
    try:
        return int(path.read_text().strip())
    except FileNotFoundError:
        return 0
    except ValueError:
        logger.warning("Invalid checkpoint file, resetting to 0: %s", path)
        return 0


def write_checkpoint(path: Path, since_ms: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(since_ms))


def _read_cached_token(path: Path) -> str | None:
    try:
        raw = path.read_text().strip()
    except FileNotFoundError:
        return None
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    token = payload.get("access_token") if isinstance(payload, dict) else None
    return token or None


def _write_cached_token(path: Path, token: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "access_token": token,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    )
    try:
        os.chmod(path, 0o600)
    except OSError:
        logger.warning("Unable to set permissions on token cache: %s", path)


def _resolve_access_token(settings: Settings) -> str:
    if settings.lichess_token:
        return settings.lichess_token
    cached = _read_cached_token(settings.lichess_token_cache_path)
    return cached or ""


def _extract_status_code(exc: BaseException) -> int | None:
    for attr in ("status", "status_code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    return status_code if isinstance(status_code, int) else None


def _is_auth_error(exc: BaseException) -> bool:
    status_code = _extract_status_code(exc)
    return status_code in {401, 403}


def _refresh_lichess_token(settings: Settings) -> str:
    refresh_token = settings.lichess_oauth_refresh_token
    client_id = settings.lichess_oauth_client_id
    client_secret = settings.lichess_oauth_client_secret
    token_url = settings.lichess_oauth_token_url
    if not refresh_token or not client_id or not client_secret:
        raise ValueError("Missing Lichess OAuth refresh token configuration")
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
    payload = response.json()
    access_token = payload.get("access_token")
    if not access_token:
        raise ValueError("Missing access_token in Lichess OAuth response")
    settings.lichess_token = access_token
    _write_cached_token(settings.lichess_token_cache_path, access_token)
    return access_token


def build_client(settings: Settings) -> berserk.Client:
    token = _resolve_access_token(settings)
    session = berserk.TokenSession(token)
    return berserk.Client(session=session)


def _fetch_remote_games_once(
    settings: Settings, since_ms: int, until_ms: int | None = None
) -> List[LichessGameRow]:
    client = build_client(settings)
    logger.info("Fetching Lichess games for user=%s since=%s", settings.user, since_ms)
    games: List[LichessGameRow] = []
    perf_value = settings.lichess_profile or settings.rapid_perf
    perf_type = _coerce_perf_type(perf_value)
    for pgn in client.games.export_by_player(
        settings.user,
        since=since_ms or None,
        until=until_ms or None,
        perf_type=perf_type,
        evals=False,
        clocks=True,
        moves=True,
        opening=True,
        max=200,
    ):
        if pgn is None:
            continue
        if isinstance(pgn, (bytes, bytearray)):
            pgn_text = pgn.decode("utf-8", errors="replace")
        else:
            pgn_text = str(pgn)
        game_id = extract_game_id(pgn_text)
        last_ts = extract_last_timestamp_ms(pgn_text)
        games.append(
            {
                "game_id": game_id,
                "user": settings.user,
                "source": settings.source,
                "fetched_at": datetime.now(timezone.utc),
                "pgn": pgn_text,
                "last_timestamp_ms": last_ts,
            }
        )
    logger.info("Fetched %s PGNs", len(games))
    return games


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def _fetch_remote_games(
    settings: Settings, since_ms: int, until_ms: int | None = None
) -> List[LichessGameRow]:
    try:
        return _fetch_remote_games_once(settings, since_ms, until_ms)
    except Exception as exc:
        if _is_auth_error(exc) and settings.lichess_oauth_refresh_token:
            logger.warning("Refreshing Lichess OAuth token after auth failure")
            _refresh_lichess_token(settings)
            return _fetch_remote_games_once(settings, since_ms, until_ms)
        raise


def fetch_incremental_games(
    settings: Settings, since_ms: int, until_ms: int | None = None
) -> List[LichessGameRow]:
    if not settings.lichess_token and settings.use_fixture_when_no_token:
        return _load_fixture_games(settings, since_ms, until_ms)
    return _fetch_remote_games(settings, since_ms, until_ms)
