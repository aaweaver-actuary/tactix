# pylint: skip-file
"""Compatibility wrapper for fetch progress context (duplicate)."""

from tactix.context_exports import FETCH_PROGRESS_CONTEXT_EXPORTS
from tactix.DailySyncStartContext import FetchProgressContext  # noqa: F401

__all__ = list(FETCH_PROGRESS_CONTEXT_EXPORTS)
