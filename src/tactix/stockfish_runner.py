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
        self.applied_options: dict[str, object] = {}

    def __enter__(self) -> "StockfishEngine":
        self._start_engine()
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:  # type: ignore[override]
        if self.engine:
            self.engine.quit()

    def restart(self) -> None:
        if self.engine:
            try:
                self.engine.quit()
            except (
                chess.engine.EngineError,
                chess.engine.EngineTerminatedError,
                OSError,
            ):
                logger.warning("Stockfish engine failed to quit cleanly; restarting")
        self.engine = None
        self._start_engine()

    def _resolve_command(self) -> Optional[str]:
        configured = str(Path(self.settings.stockfish_path))
        path = Path(configured)
        if path.exists():
            return str(path)
        resolved = shutil.which(configured)
        if resolved:
            self.settings.stockfish_path = Path(resolved)
            return resolved
        return None

    def _build_engine_options(self) -> dict[str, object]:
        return {
            "Threads": self.settings.stockfish_threads,
            "Hash": self.settings.stockfish_hash_mb,
            "Skill Level": self.settings.stockfish_skill_level,
            "UCI_AnalyseMode": self.settings.stockfish_uci_analyse_mode,
            "UCI_LimitStrength": self.settings.stockfish_limit_strength,
            "UCI_Elo": self.settings.stockfish_uci_elo,
            "Use NNUE": self.settings.stockfish_use_nnue,
            "MultiPV": self.settings.stockfish_multipv,
            "Random Seed": self.settings.stockfish_random_seed,
            "Seed": self.settings.stockfish_random_seed,
        }

    def _configure_engine(self) -> None:
        if not self.engine:
            return
        options = self.engine.options
        desired = self._build_engine_options()
        applied: dict[str, object] = {}
        for name, value in desired.items():
            if value is None:
                continue
            if name in options:
                option_meta = options[name]
                is_managed_attr = getattr(option_meta, "is_managed", None)
                if is_managed_attr is not None:
                    is_managed = (
                        is_managed_attr()
                        if callable(is_managed_attr)
                        else bool(is_managed_attr)
                    )
                else:
                    is_managed = bool(getattr(option_meta, "managed", False))
                if is_managed:
                    continue
                applied[name] = value
        if applied:
            self.engine.configure(applied)
        self.applied_options = dict(applied)
        engine_id = getattr(self.engine, "id", {})
        engine_name = engine_id.get("name") if isinstance(engine_id, dict) else None
        logger.info(
            "Stockfish configured (%s) with options: %s",
            engine_name or "unknown",
            applied,
        )

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

    def _start_engine(self) -> None:
        command = self._resolve_command()
        if command:
            logger.info("Starting Stockfish via %s", command)
            self.engine = chess.engine.SimpleEngine.popen_uci(command)
            self._configure_engine()
        else:
            logger.warning(
                "Stockfish binary not found (configured=%s); using material heuristic",
                self.settings.stockfish_path,
            )
            self.engine = None

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
