# pylint: skip-file
"""Compatibility wrapper for no-games context."""

from tactix.context_exports import NO_GAMES_CONTEXT_EXPORTS
from tactix.DailySyncStartContext import NoGamesContext  # noqa: F401

__all__ = list(NO_GAMES_CONTEXT_EXPORTS)