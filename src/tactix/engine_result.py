from __future__ import annotations

from dataclasses import dataclass

import chess
import chess.engine


@dataclass(slots=True)
class EngineResult:
    best_move: chess.Move | None
    score_cp: int
    depth: int
    mate_in: int | None = None

    @classmethod
    def from_engine_result(cls, result: chess.engine.AnalysisResult) -> EngineResult:
        score = result.get("score")
        if not hasattr(score, "pov"):
            return cls(best_move=None, score_cp=0, depth=0)
        pov_score = score.pov(result.board.turn)
        mate_in = pov_score.mate()
        value = pov_score.score(mate_score=100000)
        best_move = result.get("pv", [None])[0]
        return cls(
            best_move=best_move,
            score_cp=int(value or 0),
            depth=result.get("depth", 0),
            mate_in=mate_in,
        )

    @classmethod
    def empty(cls) -> EngineResult:
        return cls(best_move=None, score_cp=0, depth=0)
