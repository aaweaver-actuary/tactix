from __future__ import annotations

from pathlib import Path

import chess
import chess.engine

from tactix.define_stockfish_settings__config import StockfishSettings
from tactix.engine_result import EngineResult
from tactix.utils import Logger, funclogger

logger = Logger(__name__)


class StockfishEngine(chess.engine.SimpleEngine):
    @funclogger
    def __init__(self, **kwargs) -> None:
        self.settings = StockfishSettings(
            path=kwargs.get("path", "/usr/local/bin/stockfish"),
            depth=int(kwargs.get("depth", "20")),
            multipv=int(kwargs.get("multipv", 5)),
        )
        super().__init__()  # type: ignore[missing-argument]

        self._cached_result = None

    @property
    def path(self) -> Path:
        return self.settings.path

    @property
    def limit(self) -> chess.engine.Limit:
        return self.settings.limit

    @property
    def multipv(self) -> int | None:
        return self.settings.multipv

    @property
    def depth(self) -> int | None:
        if isinstance(self.limit, chess.engine.Limit):
            return self.limit.depth
        return None

    @property
    def cached_result(self) -> EngineResult | None:
        return self._cached_result

    @property
    def result(self) -> EngineResult | None:
        return self._cached_result

    def engine_result(self, board: chess.Board) -> EngineResult:
        self._run_engine_analysis(board)
        return self.cached_result or EngineResult.empty()

    @funclogger
    def analyse(self, board: chess.Board) -> EngineResult:
        return self.engine_result(board)

    @funclogger
    def _run_engine_analysis(self, board: chess.Board):
        self._engine_result = EngineResult.from_engine_result(
            self.analyse(
                board,
                limit=self.limit,
                multipv=self.multipv,
                options={"Clear Hash": True},
            )
        )
