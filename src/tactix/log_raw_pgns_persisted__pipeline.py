from __future__ import annotations

from tactix.config import Settings
from tactix.pipeline_state__pipeline import GameRow, logger


def _log_raw_pgns_persisted(
    settings: Settings,
    raw_pgns_inserted: int,
    raw_pgns_hashed: int,
    raw_pgns_matched: int,
    games_to_process: list[GameRow],
) -> None:
    logger.info(
        "Raw PGNs persisted: raw_pgns_inserted=%s raw_pgns_hashed=%s "
        "raw_pgns_matched=%s source=%s total=%s",
        raw_pgns_inserted,
        raw_pgns_hashed,
        raw_pgns_matched,
        settings.source,
        len(games_to_process),
    )
