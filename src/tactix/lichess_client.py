from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Iterable, List

import berserk
import chess.pgn

from tactix.config import Settings
from tactix.logging_utils import get_logger

logger = get_logger(__name__)

SITE_RE = re.compile(r"lichess\.org/([A-Za-z0-9]{8})")
FIXTURE_SPLIT_RE = re.compile(r"\n\n(?=\[Event )")


def _extract_game_id(pgn: str) -> str:
    game = chess.pgn.read_game(StringIO(pgn))
    if game and "Site" in game.headers:
        match = SITE_RE.search(game.headers.get("Site", ""))
        if match:
            return match.group(1)
    return str(abs(hash(pgn)))


def _extract_last_timestamp_ms(pgn: str) -> int:
    game = chess.pgn.read_game(StringIO(pgn))
    if not game:
        return int(time.time() * 1000)
    utc_date = game.headers.get("UTCDate")
    utc_time = game.headers.get("UTCTime")
    if utc_date and utc_time:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M:%S"):
            try:
                dt = datetime.strptime(f"{utc_date} {utc_time}", fmt).replace(
                    tzinfo=timezone.utc
                )
                return int(dt.timestamp() * 1000)
            except ValueError:
                continue
    return int(time.time() * 1000)


def _load_fixture_games(settings: Settings, since_ms: int) -> List[dict]:
    path = settings.fixture_pgn_path
    if not path.exists():
        logger.warning("Fixture PGN path missing: %s", path)
        return []

    chunks = [
        chunk.strip()
        for chunk in FIXTURE_SPLIT_RE.split(path.read_text())
        if chunk.strip()
    ]
    games: List[dict] = []
    for raw in chunks:
        last_ts = _extract_last_timestamp_ms(raw)
        if since_ms and last_ts <= since_ms:
            continue
        games.append(
            {
                "game_id": _extract_game_id(raw),
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
    return berserk.Client(session=session, timeout=15)


def fetch_incremental_games(settings: Settings, since_ms: int) -> List[dict]:
    if not settings.lichess_token and settings.use_fixture_when_no_token:
        return _load_fixture_games(settings, since_ms)

    client = build_client(settings)
    logger.info("Fetching Lichess games for user=%s since=%s", settings.user, since_ms)
    games: List[dict] = []
    for pgn in client.games.export_by_player(
        settings.user,
        since=since_ms or None,
        perf_type=settings.rapid_perf,
        evals=False,
        clocks=True,
        moves=True,
        opening=True,
        max=200,
    ):
        game_id = _extract_game_id(pgn)
        last_ts = _extract_last_timestamp_ms(pgn)
        games.append(
            {
                "game_id": game_id,
                "user": settings.user,
                "source": settings.source,
                "fetched_at": datetime.now(timezone.utc),
                "pgn": pgn,
                "last_timestamp_ms": last_ts,
            }
        )
    logger.info("Fetched %s PGNs", len(games))
    return games


def latest_timestamp(rows: Iterable[dict]) -> int:
    ts = 0
    for row in rows:
        ts = max(ts, int(row.get("last_timestamp_ms", 0)))
    return ts
