# pylint: skip-file
"""Compatibility wrapper for daily sync payload context."""

from tactix.context_exports import DAILY_SYNC_PAYLOAD_CONTEXT_EXPORTS
from tactix.DailySyncStartContext import DailySyncPayloadContext  # noqa: F401

__all__ = list(DAILY_SYNC_PAYLOAD_CONTEXT_EXPORTS)