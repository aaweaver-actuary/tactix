from dataclasses import dataclass

import chess

from tactix._apply_outcome_overrides import _apply_outcome_overrides
from tactix._build_tactic_rows import TacticRowInput, _build_tactic_rows
from tactix._compare_move__best_line import BestLineContext, _compare_move__best_line
from tactix._compute_eval__failed_attempt_threshold import (
    _compute_eval__failed_attempt_threshold,
)
from tactix._compute_eval__hanging_piece_unclear_threshold import (
    _compute_eval__hanging_piece_unclear_threshold,
)
from tactix._compute_severity__tactic import (
    SeverityContext,
    _compute_severity__tactic,
)
from tactix._evaluate_engine_position import _evaluate_engine_position
from tactix._infer_hanging_or_detected_motif import _infer_hanging_or_detected_motif
from tactix._override_motif_for_missed import _override_motif_for_missed
from tactix._parse_user_move import _parse_user_move
from tactix._prepare_position_inputs import _prepare_position_inputs
from tactix._reclassify_failed_attempt import _reclassify_failed_attempt
from tactix._score_after_move import _score_after_move
from tactix.config import Settings
from tactix.detect_tactics__motifs import BaseTacticDetector
from tactix.format_tactics__explanation import format_tactic_explanation
from tactix.outcome_context import BaseOutcomeContext, OutcomeOverridesContext
from tactix.StockfishEngine import StockfishEngine


@dataclass(frozen=True)
class MotifResolutionContext:
    result: str
    delta: int
    user_motif: str
    best_move_obj: object | None
    motif_board: object
    mover_color: bool


@dataclass(frozen=True)
class InitialResultContext:
    best_move: str | None
    best_move_obj: chess.Move | None
    user_move: chess.Move
    user_move_uci: str
    base_cp: int
    after_cp: int


@dataclass(frozen=True)
class PositionMotifContext:
    result: str
    delta: int
    motif_board: chess.Board
    user_move: chess.Move
    best_move_obj: chess.Move | None
    mover_color: bool


@dataclass(frozen=True)
class OutcomeOverridePositionContext:
    result: str
    motif: str
    best_move: str | None
    user_move_uci: str
    swing: int | None
    after_cp: int
    best_motif: str | None
    mate_in_one: bool
    mate_in_two: bool
    settings: Settings | None


def _resolve_motif_and_result(
    context: MotifResolutionContext,
) -> tuple[str, str, str | None]:
    result = context.result
    user_motif = context.user_motif
    motif = user_motif
    best_motif: str | None = None
    if result in {"missed", "failed_attempt", "unclear"} and context.best_move_obj is not None:
        best_motif = _infer_hanging_or_detected_motif(
            context.motif_board,
            context.best_move_obj,
            context.mover_color,
        )
        motif = _override_motif_for_missed(user_motif, best_motif, result)
    result = _reclassify_failed_attempt(result, context.delta, motif, user_motif)
    return result, motif, best_motif


def _adjust_hanging_piece_result(
    result: str,
    motif: str,
    swing: int | None,
    settings: Settings | None,
) -> str:
    if not _should_adjust_hanging_piece(result, motif, swing):
        return result
    adjusted = _resolve_hanging_piece_adjustment(result, swing, settings)
    return result if adjusted is None else adjusted


def _should_adjust_hanging_piece(
    result: str,
    motif: str,
    swing: int | None,
) -> bool:
    return all(
        (
            motif == "hanging_piece",
            swing is not None,
            result not in {"found", "failed_attempt"},
        )
    )


def _resolve_hanging_piece_adjustment(
    result: str,
    swing: int | None,
    settings: Settings | None,
) -> str | None:
    if swing is None:
        return None
    failed_attempt_threshold = _compute_eval__failed_attempt_threshold(
        "hanging_piece",
        settings,
    )
    unclear_threshold = _compute_eval__hanging_piece_unclear_threshold(settings)
    if failed_attempt_threshold is None or unclear_threshold is None:
        return None
    return _classify_hanging_piece_result(result, swing, unclear_threshold)


def _classify_hanging_piece_result(result: str, swing: int, unclear_threshold: int) -> str:
    severe_failed_attempt_threshold = unclear_threshold * 3
    if result == "missed" and swing <= severe_failed_attempt_threshold:
        return "failed_attempt"
    if swing <= unclear_threshold:
        return "missed"
    if swing < 0:
        return "failed_attempt"
    return "unclear"


def analyze_position(  # pylint: disable=too-many-locals
    position: dict[str, object],
    engine: StockfishEngine,
    settings: Settings | None = None,
) -> tuple[dict[str, object], dict[str, object]] | None:
    fen, user_move_uci, board, motif_board, mover_color = _prepare_position_inputs(position)

    best_move_obj, best_move, base_cp, mate_in_one, mate_in_two = _evaluate_engine_position(
        board, engine, mover_color, motif_board
    )

    user_move = _parse_user_move(board, user_move_uci, fen)
    if user_move is None:
        return None

    board.push(user_move)
    after_cp = _score_after_move(board, engine, mover_color)

    result, delta = _resolve_initial_result(
        InitialResultContext(
            best_move=best_move,
            best_move_obj=best_move_obj,
            user_move=user_move,
            user_move_uci=user_move_uci,
            base_cp=base_cp,
            after_cp=after_cp,
        )
    )
    result, motif, best_motif = _resolve_motif_for_position(
        PositionMotifContext(
            result=result,
            delta=delta,
            motif_board=motif_board,
            user_move=user_move,
            best_move_obj=best_move_obj,
            mover_color=mover_color,
        )
    )
    swing = _resolve_best_line_swing(
        BestLineContext(
            board=motif_board,
            best_move=best_move_obj,
            user_move_uci=user_move_uci,
            after_cp=after_cp,
            engine=engine,
            mover_color=mover_color,
        )
    )
    result, motif, mate_in = _apply_outcome_overrides_for_position(
        OutcomeOverridePositionContext(
            result=result,
            motif=motif,
            best_move=best_move,
            user_move_uci=user_move_uci,
            swing=swing,
            after_cp=after_cp,
            best_motif=best_motif,
            mate_in_one=mate_in_one,
            mate_in_two=mate_in_two,
            settings=settings,
        )
    )
    result = _finalize_hanging_piece_result(result, motif, swing, base_cp, settings)
    severity = _compute_severity_for_position(
        SeverityContext(
            base_cp=base_cp,
            delta=delta,
            motif=motif,
            mate_in=mate_in,
            result=result,
            settings=settings,
        )
    )
    best_san, explanation = format_tactic_explanation(fen, best_move or "", motif)
    return _build_tactic_rows(
        TacticRowInput(
            position=position,
            motif=motif,
            severity=severity,
            best_move=best_move,
            base_cp=base_cp,
            mate_in=mate_in,
            best_san=best_san,
            explanation=explanation,
            result=result,
            user_move_uci=user_move_uci,
            delta=delta,
        )
    )


def _resolve_initial_result(
    context: InitialResultContext,
) -> tuple[str, int]:
    result, delta = BaseTacticDetector.classify_result(
        context.best_move,
        context.user_move_uci,
        context.base_cp,
        context.after_cp,
    )
    if context.best_move_obj is not None and context.user_move == context.best_move_obj:
        result = "found"
    return result, delta


def _resolve_motif_for_position(
    context: PositionMotifContext,
) -> tuple[str, str, str | None]:
    user_motif = _infer_hanging_or_detected_motif(
        context.motif_board,
        context.user_move,
        context.mover_color,
    )
    return _resolve_motif_and_result(
        MotifResolutionContext(
            result=context.result,
            delta=context.delta,
            user_motif=user_motif,
            best_move_obj=context.best_move_obj,
            motif_board=context.motif_board,
            mover_color=context.mover_color,
        )
    )


def _resolve_best_line_swing(context: BestLineContext) -> int | None:
    return _compare_move__best_line(context)


def _apply_outcome_overrides_for_position(
    context: OutcomeOverridePositionContext,
) -> tuple[str, str, int | None]:
    return _apply_outcome_overrides(
        OutcomeOverridesContext(
            outcome=BaseOutcomeContext(
                result=context.result,
                motif=context.motif,
                best_move=context.best_move,
                user_move_uci=context.user_move_uci,
                swing=context.swing,
                after_cp=context.after_cp,
            ),
            best_motif=context.best_motif,
            after_cp=context.after_cp,
            mate_in_one=context.mate_in_one,
            mate_in_two=context.mate_in_two,
            settings=context.settings,
        )
    )


def _finalize_hanging_piece_result(
    result: str,
    motif: str,
    swing: int | None,
    base_cp: int,
    settings: Settings | None,
) -> str:
    if motif == "hanging_piece" and result == "found" and base_cp < 0:
        result = "missed"
    return _adjust_hanging_piece_result(result, motif, swing, settings)


def _compute_severity_for_position(context: SeverityContext) -> int:
    return _compute_severity__tactic(context)
