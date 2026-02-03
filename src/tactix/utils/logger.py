from __future__ import annotations

import logging
import sys
import time
from functools import wraps

_DEFAULT_LOGGER_NAME = "tactix"
_DEFAULT_LOG_LEVEL = logging.INFO
_DEFAULT_FORMATTER = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
_DEFAULT_HANDLER = logging.StreamHandler(sys.stdout)
_DEFAULT_HANDLER.setFormatter(_DEFAULT_FORMATTER)


def _configure_logger(logger: logging.Logger, level: int) -> None:
    """
    Configures a logger with the specified logging level and default handler.

    If the logger's level is not set, this function sets it to the provided level.
    It also ensures that a default handler is attached if no handlers are present,
    and disables propagation to ancestor loggers.

    Parameters
    ----------
    logger : logging.Logger
        The logger instance to configure.
    level : int
        The logging level to set if the logger's level is not already set.

    Returns
    -------
    None

    Raises
    ------
    None

    Examples
    --------
    >>> import logging
    >>> from tactix.utils.logger import _configure_logger
    >>> logger = logging.getLogger("my_logger")
    >>> _configure_logger(logger, logging.INFO)
    >>> logger.info("This is an info message.")

    Commentary
    ----------
    This function provides a focused utility for logger configuration, which can be
    useful in projects that require consistent logger setup. However, as a private
    function (indicated by the leading underscore), it may be better suited as part
    of a larger logging utility module rather than as a standalone function. In a
    large project, grouping related logging configuration helpers together would
    promote better organization and maintainability.
    """
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


def funclogger(func, *args, **kwargs):  # noqa: ARG001, PLR0915
    """Decorator to add logging to functions:

    Logs the function path/module/name.
    Logs the start and end of the function execution.
    Loops through args and kwargs to log their values.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):  # noqa: PLR0915
        module_name = func.__module__
        function_name = func.__qualname__
        full_name = f"{module_name}.{function_name}"
        function_path = full_name.replace("<", "").replace(">", "")

        logger = get_logger(function_path)

        logger.debug(f"Path: {function_path}")
        logger.debug(f"Module: {module_name}")
        logger.debug(f"Function: {function_name}")
        logger.debug("\nArgs:")
        logger.debug("-----")
        for i, arg in enumerate(args):
            logger.debug(f" {i}. {arg} ({type(arg).__name__})")

        logger.debug("\nKwargs:")
        logger.debug("-------")
        for key, value in kwargs.items():
            logger.debug(f" - {key} ({type(value).__name__}): {value}")

        logger.debug(f"Starting {function_name}")
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.debug(f"Finished {function_name} in {elapsed_time:.4f} seconds")
        logger.debug(f"Return Value: {result} ({type(result).__name__})")
        return result

    return wrapper
