from __future__ import annotations

import time

import chess.engine

from tactix.analyze_position import analyze_position
from tactix.config import Settings
from tactix.utils import Logger, funclogger

logger = Logger(__name__)


@funclogger
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
            OSError,
        ) as exc:
            if attempt >= max_retries:
                raise
            _handle_stockfish_retry(engine, attempt + 1, max_retries, exc, backoff_seconds)
    return None


def analyse_with_retries(
    engine,
    position: dict[str, object],
    settings: Settings,
) -> tuple[dict[str, object], dict[str, object]] | None:
    return _analyse_with_retries(engine, position, settings)


@funclogger
def _analyse_position__pipeline(
    position: dict[str, object],
    engine,
    settings: Settings,
) -> tuple[dict[str, object], dict[str, object]] | None:
    """
    Analyzes a chess position using the provided engine and settings,
    with support for pipeline integration.

    Args:
        position (dict[str, object]): The chess position to analyze, represented as a dictionary.
        engine: The chess engine instance to use for analysis.
        settings (Settings): Configuration settings for the analysis.

    Returns:
        tuple[dict[str, object], dict[str, object]] | None:
            A tuple containing the analysis results and additional information as dictionaries,
            or None if the analysis could not be performed.
    """
    from importlib import import_module  # noqa: PLC0415

    pipeline_module = import_module("tactix.pipeline")
    analyze_fn = getattr(pipeline_module, "analyze_position", analyze_position)
    return analyze_fn(position, engine, settings=settings)


@funclogger
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


@funclogger
def _sleep_with_backoff(backoff_seconds: float, attempt: int) -> None:
    if backoff_seconds:
        time.sleep(backoff_seconds * (2 ** (attempt - 1)))
