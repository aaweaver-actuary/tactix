"""Compatibility wrapper for no-games-after-dedupe payload context."""

from tactix.context_exports import NO_GAMES_AFTER_DEDUPE_PAYLOAD_CONTEXT_EXPORTS
from tactix.sync_contexts import NoGamesAfterDedupePayloadContext  # noqa: F401

__all__ = list(NO_GAMES_AFTER_DEDUPE_PAYLOAD_CONTEXT_EXPORTS)