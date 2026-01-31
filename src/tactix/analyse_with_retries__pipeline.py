from __future__ import annotations

import chess.engine

from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import logger
from tactix.run_stockfish__engine import StockfishEngine


def _analyse_with_retries(
    engine: StockfishEngine, position: dict[str, object], settings: Settings
) -> tuple[dict[str, object], dict[str, object]] | None:
    from tactix import pipeline as pipeline_module  # noqa: PLC0415

    max_retries = max(settings.stockfish_max_retries, 0)
    backoff_seconds = max(settings.stockfish_retry_backoff_ms, 0) / 1000.0
    attempt = 0
    while True:
        try:
            return pipeline_module.analyze_position(position, engine, settings=settings)
        except (
            chess.engine.EngineTerminatedError,
            chess.engine.EngineError,
            BrokenPipeError,
            OSError,
        ) as exc:
            attempt += 1
            if attempt > max_retries:
                raise
            logger.warning(
                "Stockfish error on attempt %s/%s: %s; restarting engine",
                attempt,
                max_retries,
                exc,
            )
            engine.restart()
            if backoff_seconds:
                pipeline_module.time.sleep(backoff_seconds * (2 ** (attempt - 1)))
