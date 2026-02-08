"""Persist operational events to Postgres."""

from tactix.db.postgres_ops_repository import record_ops_event

__all__ = ["record_ops_event"]
