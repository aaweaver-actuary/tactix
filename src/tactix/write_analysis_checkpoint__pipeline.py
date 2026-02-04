"""Persist analysis checkpoint metadata."""

from __future__ import annotations

import json


def _write_analysis_checkpoint(checkpoint_path, signature: str, index: int) -> None:
    payload = {"signature": signature, "index": index}
    checkpoint_path.write_text(json.dumps(payload))
