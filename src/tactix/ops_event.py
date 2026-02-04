"""Ops event payload model."""

from __future__ import annotations

from dataclasses import dataclass

from tactix.config import Settings


@dataclass(frozen=True)
class OpsEvent:
    """Structured event metadata for operational logging."""

    settings: Settings
    component: str
    event_type: str
    source: str | None
    profile: str | None
    metadata: dict[str, object] | None = None
