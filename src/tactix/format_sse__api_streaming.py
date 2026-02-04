"""Format Server-Sent Events payloads."""

from __future__ import annotations

import json


def _format_sse(event: str, payload: dict[str, object]) -> bytes:
    """Return an SSE-formatted payload as bytes."""
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n".encode()
