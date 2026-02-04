"""Initialize the Stockfish engine process."""

from pathlib import Path

import chess.engine

from tactix.config import Settings
from tactix.utils.logger import get_logger
from tactix.verify_stockfish_checksum import verify_stockfish_checksum

logger = get_logger(__name__)


def _initialize_engine(command: str, settings: Settings) -> chess.engine.SimpleEngine | None:
    """Return a configured Stockfish engine instance or None on failure."""
    try:
        verify_stockfish_checksum(
            Path(command),
            settings.stockfish_checksum,
            mode=settings.stockfish_checksum_mode,
        )
        return chess.engine.SimpleEngine.popen_uci(command)
    except (OSError, ValueError, RuntimeError, chess.engine.EngineError) as exc:  # pragma: no cover
        logger.warning("Stockfish failed to start: %s", exc)
        return None
