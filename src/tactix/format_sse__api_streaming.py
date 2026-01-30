from __future__ import annotations

import json


def _format_sse(event: str, payload: dict[str, object]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n".encode()
