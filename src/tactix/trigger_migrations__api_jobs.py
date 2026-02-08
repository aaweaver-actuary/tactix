"""API handler for triggering migrations."""

from __future__ import annotations

from typing import Annotated

from fastapi import Query

from tactix.config import get_settings
from tactix.pipeline import run_migrations


def trigger_migrations(
    source: Annotated[str | None, Query()] = None,
) -> dict[str, object]:
    """Trigger database migrations and return status."""
    result = run_migrations(get_settings(source=source), source=source)
    return {"status": "ok", "result": result}
