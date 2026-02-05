"""Compatibility alias for progress callbacks."""

# pylint: disable=invalid-name

from __future__ import annotations

from collections.abc import Callable

ProgressCallback = Callable[[dict[str, object]], None]

__all__ = ["ProgressCallback"]
