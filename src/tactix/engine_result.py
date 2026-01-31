from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import chess
import chess.engine


@dataclass(slots=True)
class EngineResult:
    best_move: chess.Move | None
    score_cp: int
    depth: int
    mate_in: int | None = None

    @classmethod
    def from_engine_result(
        cls,
        result: chess.engine.InfoDict | chess.engine.AnalysisResult | list[chess.engine.InfoDict],
        board: chess.Board | None = None,
    ) -> EngineResult:
        info = _select_engine_info(result)
        pov_score = _resolve_pov_score(info.get("score"), board)
        if pov_score is None:
            return cls(best_move=None, score_cp=0, depth=0)
        value, mate_in = _score_value_and_mate(pov_score)
        best_move = _best_move_from_info(info)
        depth = _depth_from_info(info)
        return cls(best_move=best_move, score_cp=int(value or 0), depth=depth, mate_in=mate_in)

    @classmethod
    def empty(cls) -> EngineResult:
        return cls(best_move=None, score_cp=0, depth=0)


def _select_engine_info(
    result: chess.engine.InfoDict | chess.engine.AnalysisResult | list[chess.engine.InfoDict],
) -> chess.engine.InfoDict:
    if isinstance(result, list):
        return _select_info_from_list(cast(list[chess.engine.InfoDict], result))
    return _select_info_from_single(result)


def _resolve_pov_score(
    score: chess.engine.Score | chess.engine.PovScore | None,
    board: chess.Board | None,
) -> chess.engine.Score | None:
    if score is None:
        return None
    if isinstance(score, chess.engine.PovScore):
        return _pov_score_from_pov(score, board)
    return _pov_score_from_score(score, board)


def _score_value_and_mate(
    pov_score: chess.engine.Score,
) -> tuple[int, int | None]:
    mate_in = pov_score.mate()
    value = pov_score.score(mate_score=100000)
    return int(value or 0), mate_in


def _best_move_from_info(info: chess.engine.InfoDict) -> chess.Move | None:
    pv = info.get("pv") or []
    return pv[0] if pv else None


def _depth_from_info(info: chess.engine.InfoDict) -> int:
    return int(info.get("depth", 0) or 0)


def _select_info_from_single(
    result: chess.engine.InfoDict | chess.engine.AnalysisResult,
) -> chess.engine.InfoDict:
    return result.info if isinstance(result, chess.engine.AnalysisResult) else result


def _select_info_from_list(items: list[chess.engine.InfoDict]) -> chess.engine.InfoDict:
    if not items:
        return {}
    return next((item for item in items if item.get("multipv") == 1), items[0])


def _pov_score_from_pov(
    score: chess.engine.PovScore,
    board: chess.Board | None,
) -> chess.engine.Score:
    return score.pov(board.turn) if board is not None else score.relative


def _pov_score_from_score(
    score: chess.engine.Score | chess.engine.PovScore,
    board: chess.Board | None,
) -> chess.engine.Score | None:
    if not isinstance(score, chess.engine.Score):
        return None
    if board is not None and board.turn == chess.BLACK:
        return -score
    return score
