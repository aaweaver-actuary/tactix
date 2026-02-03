import hashlib
from pathlib import Path

from tactix.utils.logger import get_logger

logger = get_logger(__name__)


def verify_stockfish_checksum(path: Path, expected: str | None, mode: str = "warn") -> bool:
    """Verify a Stockfish binary checksum.

    Args:
        path: Path to the Stockfish binary.
        expected: Expected hex digest.
        mode: "enforce" to raise on mismatch, otherwise warn.

    Returns:
        True if checksum matches, False otherwise.
    """

    if not expected:
        return True
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest == expected:
        return True
    message = f"Stockfish checksum mismatch for {path}"
    if mode == "enforce":
        raise RuntimeError(message)
    logger.warning(message)
    return False
