from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import chess
import chess.engine
import shutil

from tactix.config import Settings
from tactix.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class EngineResult:
    best_move: Optional[chess.Move]
    score_cp: int
    depth: int


class StockfishEngine(AbstractContextManager["StockfishEngine"]):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine: Optional[chess.engine.SimpleEngine] = None

    def __enter__(self) -> "StockfishEngine":
        command = self._resolve_command()
        if command:
            logger.info("Starting Stockfish via %s", command)
            self.engine = chess.engine.SimpleEngine.popen_uci(command)
            self.engine.configure(
                {
                    "Threads": self.settings.stockfish_threads,
                    "Hash": self.settings.stockfish_hash_mb,
                }
            )
        else:
            logger.warning(
                "Stockfish binary not found (configured=%s); using material heuristic",
                self.settings.stockfish_path,
            )
            self.engine = None
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:  # type: ignore[override]
        if self.engine:
            self.engine.quit()

    def _resolve_command(self) -> Optional[str]:
        configured = str(Path(self.settings.stockfish_path))
        path = Path(configured)
        if path.exists():
            return str(path)
        resolved = shutil.which(configured)
        if resolved:
            return resolved
        return None

    def analyse(self, board: chess.Board) -> EngineResult:
        if self.engine:
            limit = self._build_limit()
            info = self.engine.analyse(
                board,
                limit=limit,
                multipv=self.settings.stockfish_multipv,
                options={"Clear Hash": True},
            )
            if isinstance(info, list):
                info_primary = info[0]
            else:
                info_primary = info
            best_move = info_primary.get("pv", [None])[0]
            score = info_primary["score"].pov(board.turn).score(mate_score=100000)
            return EngineResult(
                best_move=best_move,
                score_cp=int(score or 0),
                depth=info_primary.get("depth", 0),
            )

        # Fallback heuristic based on material balance
        material_score = self._material_score(board)
        return EngineResult(best_move=None, score_cp=material_score, depth=0)

    def _build_limit(self) -> chess.engine.Limit:
        if self.settings.stockfish_depth:
            return chess.engine.Limit(depth=self.settings.stockfish_depth)
        return chess.engine.Limit(time=self.settings.stockfish_movetime_ms / 1000)

    @staticmethod
    def _material_score(board: chess.Board) -> int:
        values = {
            chess.PAWN: 100,
            chess.KNIGHT: 300,
            chess.BISHOP: 300,
            chess.ROOK: 500,
            chess.QUEEN: 900,
        }
        score = 0
        for piece_type, val in values.items():
            score += len(board.pieces(piece_type, chess.WHITE)) * val
            score -= len(board.pieces(piece_type, chess.BLACK)) * val
        return score if board.turn == chess.WHITE else -score
