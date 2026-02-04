"""Persist cached Lichess tokens to disk."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from tactix.utils.logger import get_logger

logger = get_logger(__name__)


def _write_cached_token(path: Path, token: str) -> None:
    """Write a cached OAuth token to disk.

    Args:
        path: Token cache path.
        token: Token value to persist.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "access_token": token,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
    )
    try:
        os.chmod(path, 0o600)
    except OSError:
        logger.warning("Unable to set permissions on token cache: %s", path)
