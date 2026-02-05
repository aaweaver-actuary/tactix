# pylint: skip-file
"""Compatibility wrapper for no-games-after-dedupe context."""

from tactix.context_exports import NO_GAMES_AFTER_DEDUPE_CONTEXT_EXPORTS
from tactix.DailySyncStartContext import NoGamesAfterDedupeContext  # noqa: F401

__all__ = list(NO_GAMES_AFTER_DEDUPE_CONTEXT_EXPORTS)