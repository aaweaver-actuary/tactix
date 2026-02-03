from typing import Any

from psycopg2.extras import RealDictCursor

from tactix._build_raw_pgn_summary import (
    _build_raw_pgn_summary,
)
from tactix._disabled_raw_pgn_summary import _disabled_raw_pgn_summary
from tactix._fetch_raw_pgn_summary import _fetch_raw_pgn_summary
from tactix.config import Settings
from tactix.init_pgn_schema import init_pgn_schema
from tactix.postgres_connection import postgres_connection
from tactix.postgres_pgns_enabled import postgres_pgns_enabled


def fetch_postgres_raw_pgns_summary(settings: Settings) -> dict[str, Any]:
    with postgres_connection(settings) as conn:
        if conn is None or not postgres_pgns_enabled(settings):
            return _disabled_raw_pgn_summary()
        init_pgn_schema(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sources, totals = _fetch_raw_pgn_summary(cur)
        return _build_raw_pgn_summary(sources, totals)
