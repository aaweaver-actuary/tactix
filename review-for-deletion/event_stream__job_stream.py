from __future__ import annotations

from collections.abc import Iterator
from queue import Empty, Queue
from typing import cast

from tactix.format_sse__api_streaming import _format_sse


def _event_stream(queue: Queue[object], sentinel: object) -> Iterator[bytes]:
    yield b"retry: 1000\n\n"
    while True:
        try:
            item = queue.get(timeout=1)
        except Empty:
            yield b": keep-alive\n\n"
            continue
        if item is sentinel:
            break
        event, payload = cast(tuple[str, dict[str, object]], item)
        yield _format_sse(event, payload)
