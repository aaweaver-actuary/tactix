from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, TypedDict, cast

import berserk
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


def _load_fixture_games(settings: Settings, since_ms: int) -> List[LichessGameRow]:
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


def build_client(settings: Settings) -> berserk.Client:
    token = settings.lichess_token or ""
    session = berserk.TokenSession(token)
    return berserk.Client(session=session)


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def _fetch_remote_games(settings: Settings, since_ms: int) -> List[LichessGameRow]:
    client = build_client(settings)
    logger.info("Fetching Lichess games for user=%s since=%s", settings.user, since_ms)
    games: List[LichessGameRow] = []
    perf_type = _coerce_perf_type(settings.rapid_perf)
    for pgn in client.games.export_by_player(
        settings.user,
        since=since_ms or None,
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


def fetch_incremental_games(settings: Settings, since_ms: int) -> List[LichessGameRow]:
    if not settings.lichess_token and settings.use_fixture_when_no_token:
        return _load_fixture_games(settings, since_ms)
    return _fetch_remote_games(settings, since_ms)
