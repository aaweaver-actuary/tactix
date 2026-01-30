from __future__ import annotations

import hashlib
import shutil
from collections.abc import Iterable, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import chess
import chess.engine

from tactix.config import Settings
from tactix.utils.logger import get_logger

logger = get_logger(__name__)
_MATERIAL_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 300,
    chess.BISHOP: 300,
    chess.ROOK: 500,
    chess.QUEEN: 900,
}


def _normalize_checksum(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().lower()
    return cleaned or None


def _compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_stockfish_checksum(
    binary_path: Path,
    expected_checksum: str | None,
    mode: str = "warn",
) -> bool:
    normalized = _normalize_checksum(expected_checksum)
    if not normalized:
        return True
    actual = _compute_sha256(binary_path)
    if actual == normalized:
        return True
    message = "Stockfish checksum mismatch (expected=%s, actual=%s, path=%s)"
    mode_lower = (mode or "warn").lower()
    if mode_lower == "enforce":
        raise RuntimeError(message % (normalized, actual, binary_path))
    logger.warning(message, normalized, actual, binary_path)
    return False


@dataclass(slots=True)
class EngineResult:
    best_move: chess.Move | None
    score_cp: int
    depth: int
    mate_in: int | None = None


class StockfishEngine(AbstractContextManager["StockfishEngine"]):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine: chess.engine.SimpleEngine | None = None
        self.applied_options: dict[str, str | int | None] = {}

    def __enter__(self) -> StockfishEngine:
        self._start_engine()
        return self

    def __exit__(self, _exc_type, _exc, _exc_tb) -> None:
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

    def _resolve_command(self) -> str | None:
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

    @staticmethod
    def _is_option_managed(option_meta: object) -> bool:
        is_managed_attr = getattr(option_meta, "is_managed", None)
        if is_managed_attr is not None:
            return is_managed_attr() if callable(is_managed_attr) else bool(is_managed_attr)
        return bool(getattr(option_meta, "managed", False))

    @staticmethod
    def _coerce_option_value(value: object) -> str | int | None:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, str)) or value is None:
            return value
        return None

    def _configure_engine(self) -> None:
        if not self.engine:
            return
        applied = self._collect_engine_options(self.engine.options)
        self._apply_engine_options(applied)
        self.applied_options = dict(applied)
        self._log_engine_config(applied)

    def _collect_engine_options(self, options: Mapping[str, object]) -> dict[str, str | int | None]:
        return dict(self._iter_engine_options(options))

    def _iter_engine_options(
        self, options: Mapping[str, object]
    ) -> Iterable[tuple[str, str | int | None]]:
        desired = self._build_engine_options()
        for name, value in desired.items():
            coerced = self._coerce_engine_option(name, value, options)
            if coerced is None:
                continue
            yield name, coerced

    def _coerce_engine_option(
        self,
        name: str,
        value: object,
        options: Mapping[str, object],
    ) -> str | int | None:
        if value is None:
            return None
        option_meta = options.get(name)
        if option_meta is None or self._is_option_managed(option_meta):
            return None
        return self._coerce_option_value(value)

    def _apply_engine_options(self, applied: dict[str, str | int | None]) -> None:
        engine = self.engine
        if not engine or not applied:
            return
        engine.configure(applied)

    def _log_engine_config(self, applied: dict[str, str | int | None]) -> None:
        engine = self.engine
        if not engine:
            return
        engine_id = getattr(engine, "id", {})
        engine_name = engine_id.get("name") if isinstance(engine_id, dict) else None
        logger.info(
            "Stockfish configured (%s) with options: %s",
            engine_name or "unknown",
            applied,
        )

    def analyse(self, board: chess.Board) -> EngineResult:
        if not self.engine:
            return self._material_result(board)
        return self._analyse_with_engine(board)

    def _material_result(self, board: chess.Board) -> EngineResult:
        material_score = self._material_score(board)
        return EngineResult(best_move=None, score_cp=material_score, depth=0)

    def _analyse_with_engine(self, board: chess.Board) -> EngineResult:
        info = self._run_engine_analysis(board)
        info_primary = self._primary_info(info)
        best_move = self._best_move_from_info(info_primary)
        score_cp, mate_in = self._score_from_info(info_primary, board.turn)
        depth = self._depth_from_info(info_primary)
        return EngineResult(
            best_move=best_move,
            score_cp=score_cp,
            depth=depth,
            mate_in=mate_in,
        )

    def _run_engine_analysis(self, board: chess.Board) -> object:
        engine = self.engine
        if engine is None:
            return {}
        limit = self._build_limit()
        return engine.analyse(
            board,
            limit=limit,
            multipv=self.settings.stockfish_multipv,
            options={"Clear Hash": True},
        )

    def _primary_info(self, info: object) -> dict[str, object]:
        if isinstance(info, list):
            if info and isinstance(info[0], dict):
                return cast(dict[str, object], info[0])
            return {}
        if isinstance(info, dict):
            return cast(dict[str, object], info)
        return {}

    def _best_move_from_info(self, info_primary: dict[str, object]) -> chess.Move | None:
        pv = info_primary.get("pv")
        if isinstance(pv, list) and pv and isinstance(pv[0], chess.Move):
            return pv[0]
        return None

    def _score_from_info(
        self, info_primary: dict[str, object], turn: bool
    ) -> tuple[int, int | None]:
        score_obj = info_primary.get("score")
        if score_obj is None:
            return 0, None
        if not hasattr(score_obj, "pov"):
            return 0, None
        score = cast(chess.engine.PovScore, score_obj)
        pov_score = score.pov(turn)
        mate_in = pov_score.mate()
        value = pov_score.score(mate_score=100000)
        return int(value or 0), mate_in

    def _depth_from_info(self, info_primary: dict[str, object]) -> int:
        depth_value = info_primary.get("depth")
        return int(depth_value) if isinstance(depth_value, (int, float)) else 0

    def _start_engine(self) -> None:
        command = self._resolve_command()
        if command:
            logger.info("Starting Stockfish via %s", command)
            verify_stockfish_checksum(
                Path(command),
                self.settings.stockfish_checksum,
                self.settings.stockfish_checksum_mode,
            )
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
        score = 0
        for piece_type, val in _MATERIAL_VALUES.items():
            score += len(board.pieces(piece_type, chess.WHITE)) * val
            score -= len(board.pieces(piece_type, chess.BLACK)) * val
        return score if board.turn == chess.WHITE else -score
