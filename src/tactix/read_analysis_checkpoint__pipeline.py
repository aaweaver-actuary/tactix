"""Read analysis checkpoint data from disk."""

from __future__ import annotations

import json


def _read_analysis_checkpoint(checkpoint_path, signature: str) -> int:
    """Return the checkpoint index for the signature or -1."""
    if not checkpoint_path.exists():
        return -1
    try:
        data = json.loads(checkpoint_path.read_text())
    except json.JSONDecodeError:
        return -1
    if data.get("signature") != signature:
        return -1
    return int(data.get("index", -1))
