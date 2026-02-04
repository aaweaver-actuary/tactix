"""Tests for stream jobs API wrapper."""

from __future__ import annotations

import importlib

from fastapi.responses import StreamingResponse

import tactix.stream_jobs__api as stream_jobs_api


def test_stream_jobs_uses_stream_job_response(monkeypatch) -> None:
    stream_jobs_api_reloaded = importlib.reload(stream_jobs_api)
    sentinel = StreamingResponse(iter(()))

    def fake_stream_job_response(request, *, get_settings):
        assert request.job == "daily_game_sync"
        return sentinel

    monkeypatch.setattr(stream_jobs_api_reloaded, "_stream_job_response", fake_stream_job_response)
    response = stream_jobs_api_reloaded.stream_jobs()
    assert response is sentinel
