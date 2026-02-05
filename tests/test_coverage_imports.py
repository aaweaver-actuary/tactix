"""Coverage smoke tests for lightweight modules."""

from __future__ import annotations

import importlib

MODULES = [
    "tactix.sync_contexts",
    "tactix.define_db_schemas__const",
    "tactix._normalize_clock_parts",
    "tactix._match_site_id",
    "tactix.airflow_settings",
    "tactix.dashboard_cache_state__api_cache",
    "tactix.StockfishEngine",
    "tactix.stockfish_runner",
]


def test_import_small_context_modules() -> None:
    for module_name in MODULES:
        module = importlib.import_module(module_name)
        assert module is not None
