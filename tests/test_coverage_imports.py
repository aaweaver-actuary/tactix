"""Coverage smoke tests for lightweight modules."""

from __future__ import annotations

import importlib

MODULES = [
    "tactix.DailySyncStartContext",
    "tactix.FetchProgressContext_1",
    "tactix.FetchProgressContext_2",
    "tactix.NoGamesAfterDedupeContext",
    "tactix.NoGamesAfterDedupePayloadContext",
    "tactix.NoGamesAfterDedupePayloadContext_1",
    "tactix.NoGamesContext",
    "tactix.NoGamesPayloadContext",
    "tactix.NoGamesPayloadContext_1",
    "tactix.PGN_SCHEMA",
    "tactix.airflow_settings",
    "tactix.dashboard_cache_state__api_cache",
    "tactix.StockfishEngine",
    "tactix.stockfish_runner",
]


def test_import_small_context_modules() -> None:
    for module_name in MODULES:
        module = importlib.import_module(module_name)
        assert module is not None
