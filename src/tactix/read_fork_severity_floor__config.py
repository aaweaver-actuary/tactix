from __future__ import annotations

import os


def _read_fork_severity_floor() -> float | None:
    value = os.getenv("TACTIX_FORK_SEVERITY_FLOOR")
    if not value:
        return None
    return float(value)
