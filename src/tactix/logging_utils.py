from __future__ import annotations

import logging
import sys
from typing import Optional


def get_logger(name: str = "tactix", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def set_level(level: int) -> None:
    for logger_name in ("tactix", "airflow", "uvicorn"):
        logging.getLogger(logger_name).setLevel(level)
