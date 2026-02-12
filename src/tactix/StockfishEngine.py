"""Stockfish engine wrapper used by analysis pipelines."""

# pylint: disable=invalid-name

from __future__ import annotations

import shutil
from contextlib import suppress
from pathlib import Path
from typing import Any

import chess
import chess.engine

from tactix._apply_engine_options import (
    _apply_engine_options,
)
from tactix._engine_command_available import _engine_command_available
from tactix._initialize_engine import _initialize_engine
from tactix.config import Settings
from tactix.engine_result import EngineResult


class StockfishEngine:  # pylint: disable=protected-access
    """Thin wrapper around python-chess engine handling config and fallbacks."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the engine wrapper with settings."""
        self.settings = settings
        self.engine: chess.engine.SimpleEngine | None = None
        self.applied_options: dict[str, Any] = {}

    def __enter__(self) -> StockfishEngine:
        """Enter context by starting the engine if needed."""
        if self.engine is None and self._should_start_engine():
            self._start_engine()
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        """Exit context by closing the engine."""
        self.close()

    def close(self) -> None:
        """Shut down the engine if running."""
        if self.engine is None:
            return
        with suppress(chess.engine.EngineError):
            self.engine.quit()
        self.engine = None

    def restart(self) -> None:
        """Restart the engine process."""
        if self.engine is not None:
            with suppress(chess.engine.EngineError):
                self.engine.quit()
        self.engine = None
        self._start_engine()

    def _resolve_command(self) -> str:
        """Resolve the stockfish binary path."""
        if self.settings.stockfish_path.exists():
            return str(self.settings.stockfish_path)
        resolved = shutil.which(str(self.settings.stockfish_path)) or shutil.which("stockfish")
        if resolved:
            self.settings.stockfish_path = Path(resolved)
            return resolved
        return str(self.settings.stockfish_path)

    def _build_limit(self) -> chess.engine.Limit:
        """Build the analysis limit for the engine."""
        if self.settings.stockfish_depth:
            return chess.engine.Limit(depth=self.settings.stockfish_depth)
        return chess.engine.Limit(time=self.settings.stockfish_movetime_ms / 1000)

    def _material_score(self, board: chess.Board) -> int:
        """Compute a basic material score for the board."""
        piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 0,
        }
        score = 0
        for piece_type, value in piece_values.items():
            score += len(board.pieces(piece_type, chess.WHITE)) * value
            score -= len(board.pieces(piece_type, chess.BLACK)) * value
        return score

    def _configure_options(self) -> dict[str, Any]:
        """Return the configured engine options."""
        options: dict[str, Any] = {
            "Threads": self.settings.stockfish_threads,
            "Hash": self.settings.stockfish_hash_mb,
            "Skill Level": self.settings.stockfish_skill_level,
            "UCI_AnalyseMode": self.settings.stockfish_uci_analyse_mode,
            "UCI_LimitStrength": self.settings.stockfish_limit_strength,
            "Use NNUE": self.settings.stockfish_use_nnue,
            "Random Seed": self.settings.stockfish_random_seed,
            "Seed": self.settings.stockfish_random_seed,
            "UCI_Elo": self.settings.stockfish_uci_elo,
        }
        return {name: value for name, value in options.items() if value is not None}

    def _should_start_engine(self) -> bool:
        """Return True when the engine should start."""
        return bool(self.settings._stockfish_path_overridden)

    def _start_engine(self) -> None:
        """Start the engine process if available."""
        if not self._should_start_engine():
            self._reset_engine_state()
            return
        command = self._resolve_command()
        if not _engine_command_available(command):
            self._reset_engine_state()
            return
        engine = _initialize_engine(command, self.settings)
        if engine is None:
            self._reset_engine_state()
            return
        self.engine = engine
        self.applied_options = _apply_engine_options(engine, self._configure_options())

    def _reset_engine_state(self) -> None:
        """Clear engine state to defaults."""
        self.engine = None
        self.applied_options = {}

    def analyse(self, board: chess.Board) -> EngineResult:
        """Analyze a board and return an engine result."""
        if self.engine is None:
            if self._should_start_engine():
                self._start_engine()
            if self.engine is None:
                return self._fallback_engine_result(board)
        engine = self.engine
        if engine is None:
            return self._fallback_engine_result(board)
        info = engine.analyse(
            board,
            limit=self._build_limit(),
            multipv=self.settings.stockfish_multipv,
            options={"Clear Hash": True},
        )
        return EngineResult.from_engine_result(info, board=board)

    def _fallback_engine_result(self, board: chess.Board) -> EngineResult:
        """Return a lightweight analysis result when no engine is available."""
        mate_move = self._find_mate_in_one(board)
        if mate_move is not None:
            return EngineResult(
                best_move=mate_move,
                score_cp=100000,
                depth=0,
                mate_in=1,
                best_line_uci=mate_move.uci(),
            )
        return EngineResult(
            best_move=None,
            score_cp=self._material_score(board),
            depth=0,
            best_line_uci=None,
        )

    def _find_mate_in_one(self, board: chess.Board) -> chess.Move | None:
        """Return a move that delivers immediate checkmate when available."""
        for move in board.legal_moves:
            board.push(move)
            is_mate = board.is_checkmate()
            board.pop()
            if is_mate:
                return move
        return None
