from __future__ import annotations

import hashlib
import shutil
from contextlib import suppress
from pathlib import Path
from typing import Any

import chess
import chess.engine

from tactix.config import Settings
from tactix.engine_result import EngineResult
from tactix.utils.logger import get_logger

logger = get_logger(__name__)


def verify_stockfish_checksum(path: Path, expected: str | None, mode: str = "warn") -> bool:
    """Verify a Stockfish binary checksum.

    Args:
        path: Path to the Stockfish binary.
        expected: Expected hex digest.
        mode: "enforce" to raise on mismatch, otherwise warn.

    Returns:
        True if checksum matches, False otherwise.
    """

    if not expected:
        return True
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest == expected:
        return True
    message = f"Stockfish checksum mismatch for {path}"
    if mode == "enforce":
        raise RuntimeError(message)
    logger.warning(message)
    return False


class StockfishEngine:
    """Thin wrapper around python-chess engine handling config and fallbacks."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine: chess.engine.SimpleEngine | None = None
        self.applied_options: dict[str, Any] = {}

    def __enter__(self) -> StockfishEngine:
        if self.engine is None and self._should_start_engine():
            self._start_engine()
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> bool:
        self.close()
        return False

    def close(self) -> None:
        if self.engine is None:
            return
        with suppress(chess.engine.EngineError):
            self.engine.quit()
        self.engine = None

    def restart(self) -> None:
        if self.engine is not None:
            with suppress(chess.engine.EngineError):
                self.engine.quit()
        self.engine = None
        self._start_engine()

    def _resolve_command(self) -> str:
        if self.settings.stockfish_path.exists():
            return str(self.settings.stockfish_path)
        resolved = shutil.which(str(self.settings.stockfish_path)) or shutil.which("stockfish")
        if resolved:
            self.settings.stockfish_path = Path(resolved)
            return resolved
        return str(self.settings.stockfish_path)

    def _build_limit(self) -> chess.engine.Limit:
        if self.settings.stockfish_depth:
            return chess.engine.Limit(depth=self.settings.stockfish_depth)
        return chess.engine.Limit(time=self.settings.stockfish_movetime_ms / 1000)

    def _material_score(self, board: chess.Board) -> int:
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
        return bool(self.settings._stockfish_path_overridden)

    def _start_engine(self) -> None:
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
        self.engine = None
        self.applied_options = {}

    def analyse(self, board: chess.Board) -> EngineResult:
        if self.engine is None:
            if self._should_start_engine():
                self._start_engine()
            if self.engine is None:
                return EngineResult(best_move=None, score_cp=self._material_score(board), depth=0)
        engine = self.engine
        info = engine.analyse(
            board,
            limit=self._build_limit(),
            multipv=self.settings.stockfish_multipv,
            options={"Clear Hash": True},
        )
        return EngineResult.from_engine_result(info, board=board)


def _engine_command_available(command: str) -> bool:
    return bool(Path(command).exists() or shutil.which(command))


def _initialize_engine(command: str, settings: Settings) -> chess.engine.SimpleEngine | None:
    try:
        verify_stockfish_checksum(
            Path(command),
            settings.stockfish_checksum,
            mode=settings.stockfish_checksum_mode,
        )
        return chess.engine.SimpleEngine.popen_uci(command)
    except Exception as exc:  # pragma: no cover - fallback handles failures
        logger.warning("Stockfish failed to start: %s", exc)
        return None


def _apply_engine_options(
    engine: chess.engine.SimpleEngine,
    options: dict[str, Any],
) -> dict[str, Any]:
    applied_options = _filter_supported_options(engine, options)
    return _configure_engine_options(engine, applied_options)


def _filter_supported_options(
    engine: chess.engine.SimpleEngine,
    options: dict[str, Any],
) -> dict[str, Any]:
    supported = getattr(engine, "options", {}) or {}
    return {name: value for name, value in options.items() if name in supported}


def _configure_engine_options(
    engine: chess.engine.SimpleEngine,
    applied_options: dict[str, Any],
) -> dict[str, Any]:
    if not applied_options:
        return {}
    try:
        engine.configure(applied_options)
    except chess.engine.EngineError as exc:  # pragma: no cover - engine-specific
        logger.warning("Stockfish option configuration failed: %s", exc)
    return applied_options


__all__ = ["EngineResult", "StockfishEngine", "verify_stockfish_checksum"]
