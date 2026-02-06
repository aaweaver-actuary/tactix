"""Upsert tactics and outcome rows into Postgres."""

from tactix.db.postgres_analysis_repository import upsert_analysis_tactic_with_outcome

__all__ = ["upsert_analysis_tactic_with_outcome"]
