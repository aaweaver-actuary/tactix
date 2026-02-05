"""Legacy shim for the Postgres store class."""

# pylint: disable=invalid-name

from tactix.postgres_store_impl import PostgresStore

__all__ = ["PostgresStore"]
