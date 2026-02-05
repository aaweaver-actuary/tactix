# pylint: skip-file
"""Compatibility wrapper for no-games payload context (duplicate)."""

from tactix.context_exports import NO_GAMES_PAYLOAD_CONTEXT_EXPORTS
from tactix.sync_contexts import NoGamesPayloadContext  # noqa: F401

__all__ = list(NO_GAMES_PAYLOAD_CONTEXT_EXPORTS)