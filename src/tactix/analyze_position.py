from dataclasses import dataclass

import chess

from tactix._apply_outcome_overrides import _apply_outcome_overrides
from tactix._build_tactic_rows import (
    _build_tactic_rows,
)
from tactix._compare_move__best_line import BestLineContext, _compare_move__best_line
from tactix._compute_eval__failed_attempt_threshold import (
    _compute_eval__failed_attempt_threshold,
)
from tactix._compute_eval__hanging_piece_unclear_threshold import (
    _compute_eval__hanging_piece_unclear_threshold,
)
from tactix._compute_severity__tactic import (
    SeverityContext,
    SeverityInputs,
    _compute_severity__tactic,
    build_severity_context,
)
from tactix._evaluate_engine_position import _evaluate_engine_position
from tactix._infer_hanging_or_detected_motif import _infer_hanging_or_detected_motif
from tactix._override_motif_for_missed import _override_motif_for_missed
from tactix._parse_user_move import _parse_user_move
from tactix._prepare_position_inputs import _prepare_position_inputs
from tactix._reclassify_failed_attempt import _reclassify_failed_attempt
from tactix._score_after_move import _score_after_move
from tactix.analyze_tactics__positions import (
    _FAILED_ATTEMPT_RECLASSIFY_THRESHOLDS,
)
from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.config import Settings
from tactix.format_tactics__explanation import format_tactic_explanation
from tactix.outcome_context import BaseOutcomeContext, OutcomeOverridesContext
from tactix.OutcomeDetails import OutcomeDetails
from tactix.StockfishEngine import StockfishEngine
from tactix.TacticDetails import TacticDetails
from tactix.TacticRowInput import TacticRowInput
from tactix.utils.logger import funclogger


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
    outcome: BaseOutcomeContext
    after_cp: int
    best_motif: str | None
    mate_in_one: bool
    mate_in_two: bool
    settings: Settings | None


def _capture_square_for_move(
    board: chess.Board,
    move: chess.Move,
) -> chess.Square:
    if board.is_en_passant(move):
        return move.to_square + (-8 if board.turn == chess.WHITE else 8)
    return move.to_square


def _is_moved_piece_hanging(
    board_after: chess.Board,
    move: chess.Move,
    mover_color: bool,
) -> bool:
    target_square = move.to_square
    moved_piece = board_after.piece_at(target_square)
    if moved_piece is None or moved_piece.color != mover_color:
        return False
    if not board_after.is_attacked_by(not mover_color, target_square):
        return False
    if not board_after.is_attacked_by(mover_color, target_square):
        return True
    for response in board_after.legal_moves:
        if not board_after.is_capture(response):
            continue
        capture_square = _capture_square_for_move(board_after, response)
        if capture_square != target_square:
            continue
        attacker = board_after.piece_at(response.from_square)
        if attacker is None:
            continue
        if BaseTacticDetector.piece_value(moved_piece.piece_type) > BaseTacticDetector.piece_value(
            attacker.piece_type
        ):
            return True
    return False


def _should_mark_missed_for_initiative(
    context: MotifResolutionContext,
    result: str,
    user_motif: str,
) -> bool:
    return result == "initiative" and context.best_move_obj is None and user_motif != "unknown"


def _should_infer_best_motif(result: str, best_move_obj: object | None) -> bool:
    return result in {"missed", "failed_attempt", "unclear"} and best_move_obj is not None


def _resolve_best_motif_adjustment(
    context: MotifResolutionContext,
    result: str,
    user_motif: str,
) -> tuple[str, str, str | None]:
    best_motif = _infer_hanging_or_detected_motif(
        context.motif_board,
        context.best_move_obj,
        context.mover_color,
    )
    if (
        best_motif == "initiative"
        and result in {"missed", "failed_attempt"}
        and user_motif not in _FAILED_ATTEMPT_RECLASSIFY_THRESHOLDS
    ):
        return "unclear", user_motif, best_motif
    return result, _override_motif_for_missed(user_motif, best_motif, result), best_motif


def _classify_hanging_piece_from_base(
    base_cp: int | None,
    delta: int,
    unclear_threshold: int,
) -> str | None:
    if base_cp is None:
        return None
    if base_cp < abs(unclear_threshold):
        return None
    after_cp = base_cp + delta
    if delta <= unclear_threshold < after_cp:
        return "failed_attempt"
    return None


@funclogger
def _resolve_motif_and_result(
    context: MotifResolutionContext,
) -> tuple[str, str, str | None]:
    result = context.result
    user_motif = context.user_motif
    motif = user_motif
    best_motif: str | None = None
    if _should_mark_missed_for_initiative(context, result, user_motif):
        result = "missed"
    if _should_infer_best_motif(result, context.best_move_obj):
        result, motif, best_motif = _resolve_best_motif_adjustment(
            context,
            result,
            user_motif,
        )
    result = _reclassify_failed_attempt(result, context.delta, motif, user_motif)
    return result, motif, best_motif


@funclogger
def _adjust_hanging_piece_result(
    result: str,
    motif: str,
    delta: int | None,
    base_cp: int | None,
    settings: Settings | None,
) -> str:
    if not _should_adjust_hanging_piece(result, motif, delta):
        return result
    adjusted = _resolve_hanging_piece_adjustment(result, delta, base_cp, settings)
    return result if adjusted is None else adjusted


@funclogger
def _should_adjust_hanging_piece(
    result: str,
    motif: str,
    delta: int | None,
) -> bool:
    return all(
        (
            motif == "hanging_piece",
            delta is not None,
            result != "found",
        )
    )


@funclogger
def _resolve_hanging_piece_adjustment(
    result: str,
    delta: int | None,
    base_cp: int | None,
    settings: Settings | None,
) -> str | None:
    if delta is None:
        return None
    failed_attempt_threshold = _compute_eval__failed_attempt_threshold(
        "hanging_piece",
        settings,
    )
    unclear_threshold = _compute_eval__hanging_piece_unclear_threshold(settings)
    if failed_attempt_threshold is None or unclear_threshold is None:
        return None
    return _classify_hanging_piece_result(
        result,
        delta,
        unclear_threshold,
        failed_attempt_threshold,
        base_cp,
    )


@funclogger
def _classify_hanging_piece_result(
    result: str,
    delta: int,
    unclear_threshold: int,
    failed_attempt_threshold: int,
    base_cp: int | None,
) -> str:
    if result == "unclear":
        return "unclear"
    classification = _classify_hanging_piece_from_base(base_cp, delta, unclear_threshold)
    if classification is not None:
        return classification
    if _is_missed_due_to_delta(base_cp, delta, unclear_threshold, failed_attempt_threshold):
        return "missed"
    return _classify_non_missed_delta(result, delta, failed_attempt_threshold)


def _is_missed_due_to_delta(
    base_cp: int | None,
    delta: int,
    unclear_threshold: int,
    failed_attempt_threshold: int,
) -> bool:
    if base_cp is not None and base_cp <= unclear_threshold and delta <= failed_attempt_threshold:
        return True
    return delta <= unclear_threshold


def _classify_non_missed_delta(
    result: str,
    delta: int,
    failed_attempt_threshold: int,
) -> str:
    if delta <= failed_attempt_threshold:
        return "failed_attempt"
    if delta < 0:
        return "failed_attempt" if result == "failed_attempt" else "unclear"
    return "unclear"


@funclogger
def analyze_position(
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
            outcome=BaseOutcomeContext(
                result=result,
                motif=motif,
                best_move=best_move,
                user_move_uci=user_move_uci,
                swing=swing,
                after_cp=after_cp,
            ),
            after_cp=after_cp,
            best_motif=best_motif,
            mate_in_one=mate_in_one,
            mate_in_two=mate_in_two,
            settings=settings,
        )
    )
    result = _finalize_hanging_piece_result(result, motif, delta, base_cp, settings)
    non_overrideable_hanging = {
        "fork",
        "discovered_attack",
        "discovered_check",
        "mate",
    }
    should_override_hanging = motif not in non_overrideable_hanging
    if (
        result != "found"
        and _is_moved_piece_hanging(board, user_move, mover_color)
        and should_override_hanging
        and not (motif == "skewer" and board.is_check())
    ):
        result = "missed"
        motif = "hanging_piece"
    severity = _compute_severity_for_position(
        build_severity_context(
            SeverityInputs(
                base_cp=base_cp,
                delta=delta,
                motif=motif,
                mate_in=mate_in,
                result=result,
                settings=settings,
            )
        )
    )
    best_san, explanation = format_tactic_explanation(fen, best_move or "", motif)
    return _build_tactic_rows(
        TacticRowInput(
            position=position,
            details=TacticDetails(
                motif=motif,
                severity=severity,
                best_move=best_move,
                base_cp=base_cp,
                mate_in=mate_in,
                best_san=best_san,
                explanation=explanation,
            ),
            outcome=OutcomeDetails(
                result=result,
                user_move_uci=user_move_uci,
                delta=delta,
            ),
        )
    )


@funclogger
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


@funclogger
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


@funclogger
def _resolve_best_line_swing(context: BestLineContext) -> int | None:
    return _compare_move__best_line(context)


@funclogger
def _apply_outcome_overrides_for_position(
    context: OutcomeOverridePositionContext,
) -> tuple[str, str, int | None]:
    return _apply_outcome_overrides(
        OutcomeOverridesContext(
            outcome=context.outcome,
            best_motif=context.best_motif,
            after_cp=context.after_cp,
            mate_in_one=context.mate_in_one,
            mate_in_two=context.mate_in_two,
            settings=context.settings,
        )
    )


@funclogger
def _finalize_hanging_piece_result(
    result: str,
    motif: str,
    delta: int | None,
    base_cp: int,
    settings: Settings | None,
) -> str:
    return _adjust_hanging_piece_result(result, motif, delta, base_cp, settings)


@funclogger
def _compute_severity_for_position(context: SeverityContext) -> int:
    return _compute_severity__tactic(context)
