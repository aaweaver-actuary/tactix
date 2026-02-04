from psycopg2.extensions import connection as PgConnection  # noqa: N812

from tactix._list_tables import _list_tables


def _schema_tables(conn: PgConnection, schema: str, label: str) -> list[str]:
    return [f"{label}.{name}" for name in _list_tables(conn, schema)]
