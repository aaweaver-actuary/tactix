"""Tests for applying engine options."""

from __future__ import annotations

import tactix._apply_engine_options as apply_engine_options


def test_apply_engine_options_calls_helpers(monkeypatch) -> None:
    engine = object()
    options = {"Threads": 2}

    def fake_filter_supported_options(engine_arg, options_arg):
        assert engine_arg is engine
        assert options_arg is options
        return {"Threads": 2}

    def fake_configure_engine_options(engine_arg, options_arg):
        assert engine_arg is engine
        assert options_arg == {"Threads": 2}
        return {"applied": True}

    monkeypatch.setattr(
        apply_engine_options, "_filter_supported_options", fake_filter_supported_options
    )
    monkeypatch.setattr(
        apply_engine_options, "_configure_engine_options", fake_configure_engine_options
    )

    assert apply_engine_options._apply_engine_options(engine, options) == {"applied": True}
