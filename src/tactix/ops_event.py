"""Ops event payload model."""

from __future__ import annotations

from dataclasses import dataclass

from tactix.config import Settings


@dataclass(frozen=True)
class OpsEvent:  # pylint: disable=too-many-instance-attributes
    """Structured event metadata for operational logging."""

    settings: Settings
    component: str
    event_type: str
    source: str | None
    profile: str | None
    metadata: dict[str, object] | None = None
    run_id: str | None = None
    op_id: str | None = None
