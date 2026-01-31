from __future__ import annotations

import time

import chess.engine

from tactix.config import Settings
from tactix.utils.logger import get_logger

logger = get_logger(__name__)


def _analyse_with_retries(
    engine,
    position: dict[str, object],
    settings: Settings,
) -> tuple[dict[str, object], dict[str, object]] | None:
    max_retries = max(settings.stockfish_max_retries, 0)
    backoff_seconds = max(settings.stockfish_retry_backoff_ms, 0) / 1000.0
    for attempt in range(max_retries + 1):
        try:
            return _analyse_position__pipeline(position, engine, settings)
        except (
            chess.engine.EngineTerminatedError,
            chess.engine.EngineError,
            BrokenPipeError,
            OSError,
        ) as exc:
            if attempt >= max_retries:
                raise
            _handle_stockfish_retry(engine, attempt + 1, max_retries, exc, backoff_seconds)
    return None


def _analyse_position__pipeline(
    position: dict[str, object],
    engine,
    settings: Settings,
) -> tuple[dict[str, object], dict[str, object]] | None:
    from tactix import pipeline as pipeline_module  # noqa: PLC0415

    return pipeline_module.analyze_position(position, engine, settings=settings)


def _handle_stockfish_retry(
    engine,
    attempt: int,
    max_retries: int,
    exc: Exception,
    backoff_seconds: float,
) -> None:
    logger.warning(
        "Stockfish error on attempt %s/%s: %s; restarting engine",
        attempt,
        max_retries,
        exc,
    )
    if hasattr(engine, "restart"):
        engine.restart()
    _sleep_with_backoff(backoff_seconds, attempt)


def _sleep_with_backoff(backoff_seconds: float, attempt: int) -> None:
    if backoff_seconds:
        time.sleep(backoff_seconds * (2 ** (attempt - 1)))
