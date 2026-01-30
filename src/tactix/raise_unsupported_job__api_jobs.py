from __future__ import annotations

from typing import NoReturn


def _raise_unsupported_job(job: str) -> NoReturn:
    raise ValueError(f"Unsupported job: {job}")
