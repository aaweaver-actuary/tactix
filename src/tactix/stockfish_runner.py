"""Convenience exports for Stockfish engine usage."""

from __future__ import annotations

import shutil
from pathlib import Path

from tactix.engine_result import EngineResult
from tactix.StockfishEngine import StockfishEngine
from tactix.utils.logger import Logger

logger = Logger(__name__)

__all__ = ["EngineResult", "Path", "StockfishEngine", "logger", "shutil"]
