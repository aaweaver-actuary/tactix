# pylint: skip-file
"""Compatibility wrapper for daily sync completion context."""

from tactix.context_exports import DAILY_SYNC_COMPLETE_CONTEXT_EXPORTS
from tactix.DailySyncStartContext import DailySyncCompleteContext  # noqa: F401

__all__ = list(DAILY_SYNC_COMPLETE_CONTEXT_EXPORTS)