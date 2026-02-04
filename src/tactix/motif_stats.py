"""API helpers for motif statistics."""

from typing import Annotated

from fastapi import Depends

from tactix.build_dashboard_stats_payload__api import _build_dashboard_stats_payload
from tactix.DashboardQueryFilters import DashboardQueryFilters
from tactix.db.duckdb_store import fetch_motif_stats


def motif_stats(
    filters: Annotated[DashboardQueryFilters, Depends()],
) -> dict[str, object]:
    """Return motif statistics payload for the dashboard."""
    return _build_dashboard_stats_payload(filters, fetch_motif_stats, "motifs")
