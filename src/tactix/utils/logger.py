from __future__ import annotations

import logging
import sys

_DEFAULT_LOGGER_NAME = "tactix"
_DEFAULT_LOG_LEVEL = logging.INFO
_DEFAULT_FORMATTER = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
_DEFAULT_HANDLER = logging.StreamHandler(sys.stdout)
_DEFAULT_HANDLER.setFormatter(_DEFAULT_FORMATTER)


def _configure_logger(logger: logging.Logger, level: int) -> None:
    if logger.level == logging.NOTSET:
        logger.setLevel(level)
    if not logger.handlers:
        logger.addHandler(_DEFAULT_HANDLER)
    logger.propagate = False


def get_logger(name: str | None = None, level: int = _DEFAULT_LOG_LEVEL) -> logging.Logger:
    logger = logging.getLogger(name or _DEFAULT_LOGGER_NAME)
    _configure_logger(logger, level)
    return logger


def set_level(level: int, logger_names: list[str] | None = None) -> None:
    names = logger_names or [_DEFAULT_LOGGER_NAME, "airflow", "uvicorn"]
    for name in names:
        logging.getLogger(name).setLevel(level)


class Logger(logging.Logger):
    """Custom Logger class for Tactix."""

    def __init__(self, name: str = _DEFAULT_LOGGER_NAME, level: int = _DEFAULT_LOG_LEVEL) -> None:
        super().__init__(name, level)
        _configure_logger(self, level)
