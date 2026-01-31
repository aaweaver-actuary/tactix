from __future__ import annotations

from pathlib import Path

from tactix.utils.logger import get_logger

logger = get_logger(__name__)


def read_checkpoint(path: Path) -> int:
    """Read a Lichess checkpoint value from disk.

    Args:
        path: Checkpoint path.

    Returns:
        Checkpoint timestamp in milliseconds.
    """

    try:
        return int(path.read_text().strip())
    except FileNotFoundError:
        return 0
    except ValueError:
        logger.warning("Invalid checkpoint file, resetting to 0: %s", path)
        return 0
