"""Tests for streaming response helper."""

from __future__ import annotations

import importlib
from queue import Queue

from fastapi.responses import StreamingResponse

import tactix.job_stream as streaming_response_module


def test_streaming_response_returns_streaming_response() -> None:
    streaming_response_module_reloaded = importlib.reload(streaming_response_module)
    queue: Queue[object] = Queue()
    sentinel = object()
    response = streaming_response_module_reloaded._streaming_response(queue, sentinel)
    assert isinstance(response, StreamingResponse)
