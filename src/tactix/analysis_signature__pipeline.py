from __future__ import annotations

import hashlib
import json


def _analysis_signature(game_ids: list[str], positions_count: int, source: str) -> str:
    payload = {
        "game_ids": game_ids,
        "positions_count": positions_count,
        "source": source,
    }
    serialized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
