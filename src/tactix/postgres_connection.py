from collections.abc import Iterator
from contextlib import contextmanager

import psycopg2
from psycopg2.extensions import connection as PgConnection  # noqa: N812

from tactix._connection_kwargs import _connection_kwargs
from tactix.config import Settings
from tactix.utils.logger import get_logger

logger = get_logger(__name__)


@contextmanager
def postgres_connection(settings: Settings) -> Iterator[PgConnection | None]:
    kwargs = _connection_kwargs(settings)
    if not kwargs:
        yield None
        return
    conn: PgConnection | None = None
    try:
        conn = psycopg2.connect(**kwargs)
        conn.autocommit = True
    except Exception as exc:  # pragma: no cover - handled by status endpoint
        logger.warning("Postgres connection failed: %s", exc)
        yield None
        return
    try:
        yield conn
    finally:
        if conn is not None:
            conn.close()
