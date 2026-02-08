from __future__ import annotations

import sys
import time

from tactix.config import Settings
from tactix.postgres_connection import postgres_connection


def build_table_name() -> str:
    return f"py_smoke_{int(time.time() * 1000)}"


def run() -> None:
    settings = Settings()
    with postgres_connection(settings) as conn:
        if conn is None:
            raise RuntimeError("Missing Postgres connection info")
        table = build_table_name()
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE TEMP TABLE {table} (id SERIAL PRIMARY KEY, name TEXT NOT NULL, created_at TIMESTAMPTZ DEFAULT now())"
            )
            name = f"py-{table}"
            cur.execute(
                f"INSERT INTO {table} (name) VALUES (%s) RETURNING id",
                (name,),
            )
            row_id = cur.fetchone()[0]

            cur.execute(f"SELECT COUNT(*) FROM {table}")
            inserted = cur.fetchone()[0]

            updated_name = f"py-{table}-updated"
            cur.execute(
                f"UPDATE {table} SET name = %s WHERE id = %s",
                (updated_name, row_id),
            )

            cur.execute(f"SELECT name FROM {table} WHERE id = %s", (row_id,))
            selected = cur.fetchone()[0]

            cur.execute(f"DELETE FROM {table} WHERE id = %s", (row_id,))

            cur.execute(f"SELECT COUNT(*) FROM {table}")
            remaining = cur.fetchone()[0]

            cur.execute(f"DROP TABLE {table}")

    print(
        "Python CRUD ok: inserted={}, selected='{}', remaining={}".format(
            inserted, selected, remaining
        )
    )


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # pragma: no cover
        print(f"Python Postgres smoke test failed: {exc}", file=sys.stderr)
        raise
