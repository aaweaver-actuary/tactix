"""Collect tables for Postgres housekeeping."""

from psycopg2.extensions import connection as PgConnection  # noqa: N812

from tactix._schema_tables import _schema_tables
from tactix.ANALYSIS_SCHEMA import ANALYSIS_SCHEMA
from tactix.config import Settings
from tactix.init_analysis_schema import init_analysis_schema
from tactix.init_pgn_schema import init_pgn_schema
from tactix.PGN_SCHEMA import PGN_SCHEMA


def _collect_tables(conn: PgConnection, settings: Settings) -> list[str]:
    """Return table names for schemas used by the service."""
    tables: list[str] = []
    tables.extend(_schema_tables(conn, "tactix_ops", "tactix_ops"))
    if settings.postgres_analysis_enabled:
        init_analysis_schema(conn)
        tables.extend(_schema_tables(conn, ANALYSIS_SCHEMA, ANALYSIS_SCHEMA))
    if settings.postgres_pgns_enabled:
        init_pgn_schema(conn)
        tables.extend(_schema_tables(conn, PGN_SCHEMA, PGN_SCHEMA))
    return tables
