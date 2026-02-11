from unittest.mock import MagicMock

import pytest

from tactix.sync_contexts import (
    AnalysisMetrics,
    DailySyncCheckpoint,
    DailySyncPayloadMetrics,
    DailySyncTotals,
    NoGamesWindowContext,
    RawPgnMetrics,
    _require_no_games_payload_games,
    _resolve_daily_sync_payload_metrics,
    _resolve_daily_sync_totals,
    _resolve_no_games_window_context,
    _resolve_required_kwargs,
    _validate_allowed_kwargs,
)


def test_validate_allowed_kwargs_raises_on_unknown() -> None:
    with pytest.raises(TypeError, match="Unexpected keyword arguments"):
        _validate_allowed_kwargs({"extra": 1}, {"allowed"})


def test_resolve_required_kwargs_raises_on_missing() -> None:
    with pytest.raises(TypeError, match="Missing required arguments"):
        _resolve_required_kwargs({"needed": None}, {"needed"})


def test_resolve_daily_sync_totals_rejects_unexpected_kwargs() -> None:
    totals = DailySyncTotals(
        raw_pgns_inserted=1,
        postgres_raw_pgns_inserted=1,
        positions_count=1,
        tactics_count=1,
        postgres_written=1,
        postgres_synced=1,
        metrics_version=1,
    )
    with pytest.raises(TypeError, match="Unexpected keyword arguments"):
        _resolve_daily_sync_totals(totals, {"raw_pgns_inserted": 1})


def test_resolve_daily_sync_payload_metrics_rejects_unexpected_kwargs() -> None:
    metrics = DailySyncPayloadMetrics(
        raw_pgns=RawPgnMetrics(
            raw_pgns_inserted=1,
            raw_pgns_hashed=1,
            raw_pgns_matched=1,
            postgres_raw_pgns_inserted=1,
        ),
        analysis=AnalysisMetrics(positions_count=1, tactics_count=1, metrics_version=1),
        checkpoint=DailySyncCheckpoint(checkpoint_value=None, last_timestamp_value=1),
    )
    with pytest.raises(TypeError, match="Unexpected keyword arguments"):
        _resolve_daily_sync_payload_metrics(metrics, {"positions_count": 1})


def test_resolve_no_games_window_context_rejects_unexpected_kwargs() -> None:
    window = NoGamesWindowContext(
        fetch_context=MagicMock(),
        last_timestamp_value=10,
        window_filtered=0,
    )
    with pytest.raises(TypeError, match="Unexpected keyword arguments"):
        _resolve_no_games_window_context(
            window,
            fetch_context=MagicMock(),
            last_timestamp_value=None,
            window_filtered=None,
        )


def test_require_no_games_payload_games_raises_when_missing() -> None:
    with pytest.raises(TypeError, match="Missing required arguments"):
        _require_no_games_payload_games({})
