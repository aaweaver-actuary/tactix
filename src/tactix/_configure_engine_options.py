from typing import Any

import chess.engine

from tactix.utils.logger import Logger

logger = Logger(__name__)


def _configure_engine_options(
    engine: chess.engine.SimpleEngine,
    applied_options: dict[str, Any],
) -> dict[str, Any]:
    if not applied_options:
        return {}
    try:
        engine.configure(applied_options)
    except chess.engine.EngineError as exc:  # pragma: no cover - engine-specific
        logger.warning("Stockfish option configuration failed: %s", exc)
    return applied_options
