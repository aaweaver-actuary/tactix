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
from tactix._find_hanging_capture_target import (
    HangingCaptureTarget,
    _find_hanging_capture_target,
)
from tactix._infer_hanging_or_detected_motif import _infer_hanging_or_detected_motif
from tactix._is_moved_piece_hanging_after_move import _is_moved_piece_hanging_after_move
from tactix._override_motif_for_missed import _override_motif_for_missed
from tactix._parse_user_move import _parse_user_move
from tactix._prepare_position_inputs import _prepare_position_inputs
from tactix._reclassify_failed_attempt import _reclassify_failed_attempt
from tactix._score_after_move import _score_after_move
from tactix.analyze_tactics__positions import (
    _FAILED_ATTEMPT_RECLASSIFY_THRESHOLDS,
    _OVERRIDEABLE_USER_MOTIFS,
    MATE_IN_TWO,
)
from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.config import Settings
from tactix.format_tactics__explanation import format_tactic_explanation
from tactix.outcome_context import BaseOutcomeContext, OutcomeOverridesContext
from tactix.OutcomeDetails import OutcomeDetails
from tactix.StockfishEngine import StockfishEngine
from tactix.tactic_metadata import resolve_tactic_metadata
from tactix.tactic_scope import is_supported_motif
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


@dataclass(frozen=True)
class MovedPieceHangingContext:
    board_before: chess.Board
    board_after: chess.Board
    user_move: chess.Move
    mover_color: bool


@dataclass(frozen=True)
class OpponentHangingContext:
    result: str
    motif: str
    mover_color: bool
    user_to_move: bool
    hanging_target: HangingCaptureTarget | None


@dataclass(frozen=True)
class HangingTargetContext:
    board_before: chess.Board
    board_after: chess.Board
    user_move: chess.Move
    mover_color: bool
    hanging_target: HangingCaptureTarget | None


def _capture_square_for_move(
    board: chess.Board,
    move: chess.Move,
) -> chess.Square:
    if board.is_en_passant(move):
        return move.to_square + (-8 if board.turn == chess.WHITE else 8)
    return move.to_square


def _should_override_hanging_motif(motif: str, board: chess.Board) -> bool:
    non_overrideable = {
        "fork",
        "discovered_attack",
        "discovered_check",
        "mate",
    }
    if motif in non_overrideable:
        return False
    return not (motif == "skewer" and board.is_check())


def _apply_moved_piece_hanging_override(
    result: str,
    motif: str,
    context: MovedPieceHangingContext,
) -> tuple[str, str]:
    if result == "found":
        return result, motif
    if not _is_moved_piece_hanging_after_move(
        context.board_before,
        context.board_after,
        context.user_move,
        context.mover_color,
    ):
        return result, motif
    if not _should_override_hanging_motif(motif, context.board_after):
        return result, motif
    return "missed", "hanging_piece"


def _apply_opponent_hanging_override(
    context: OpponentHangingContext,
) -> tuple[str, str]:
    return _resolve_opponent_override_result(context)


def _should_override_opponent_hanging(context: OpponentHangingContext) -> bool:
    return all(
        (
            context.user_to_move,
            context.hanging_target is not None,
            context.result in {"missed", "failed_attempt", "unclear"},
            context.motif in _OVERRIDEABLE_USER_MOTIFS,
        )
    )


def _resolve_opponent_override_result(
    context: OpponentHangingContext,
) -> tuple[str, str]:
    return (
        (context.result, "hanging_piece")
        if _should_override_opponent_hanging(context)
        else (context.result, context.motif)
    )


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
        best_motif == "unknown"
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
    tactic_input = _prepare_tactic_row_input(position, engine, settings)
    if tactic_input is None:
        return None
    return _build_tactic_rows(tactic_input)


def _prepare_tactic_row_input(  # noqa: PLR0915
    position: dict[str, object],
    engine: StockfishEngine,
    settings: Settings | None,
) -> TacticRowInput | None:
    fen, user_move_uci, board, motif_board, mover_color = _prepare_position_inputs(position)
    (
        best_move_obj,
        best_move,
        base_cp,
        mate_in_one,
        mate_in_two,
        best_line_uci,
        engine_depth,
    ) = _evaluate_engine_position(board, engine, mover_color, motif_board)
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
    hanging_target = None
    if position.get("user_to_move", True):
        hanging_target = _find_hanging_capture_target(motif_board, mover_color)
    result, motif = _apply_opponent_hanging_override(
        OpponentHangingContext(
            result=result,
            motif=motif,
            mover_color=mover_color,
            user_to_move=bool(position.get("user_to_move", True)),
            hanging_target=hanging_target,
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
    result, motif = _apply_moved_piece_hanging_override(
        result,
        motif,
        MovedPieceHangingContext(
            board_before=motif_board,
            board_after=board,
            user_move=user_move,
            mover_color=mover_color,
        ),
    )
    if not is_supported_motif(motif, mate_in):
        return None
    target_piece, target_square = _resolve_hanging_piece_target(
        motif,
        HangingTargetContext(
            board_before=motif_board,
            board_after=board,
            user_move=user_move,
            mover_color=mover_color,
            hanging_target=hanging_target,
        ),
    )
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
    best_san, explanation = format_tactic_explanation(
        fen,
        best_move or "",
        motif,
    )
    metadata = resolve_tactic_metadata(fen, best_move, motif)
    mate_type = metadata["mate_type"]
    if motif == "mate" and mate_in == MATE_IN_TWO and not mate_type:
        mate_type = "mate_in_two"
    return TacticRowInput(
        position=position,
        details=TacticDetails(
            motif=motif,
            severity=severity,
            best_move=best_move,
            best_line_uci=best_line_uci,
            base_cp=base_cp,
            engine_depth=engine_depth,
            mate_in=mate_in,
            tactic_piece=metadata["tactic_piece"],
            mate_type=mate_type,
            best_san=best_san,
            explanation=explanation,
            target_piece=target_piece,
            target_square=target_square,
        ),
        outcome=OutcomeDetails(
            result=result,
            user_move_uci=user_move_uci,
            delta=delta,
        ),
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


def _resolve_hanging_piece_target(
    motif: str,
    context: HangingTargetContext,
) -> tuple[str | None, str | None]:
    if motif != "hanging_piece":
        return None, None
    return _resolve_hanging_piece_target_for_context(context)


def _resolve_hanging_piece_target_for_context(
    context: HangingTargetContext,
) -> tuple[str | None, str | None]:
    moved_target = _resolve_moved_piece_target(context)
    return moved_target if moved_target is not None else _resolve_opponent_hanging_target(context)


def _resolve_moved_piece_target(
    context: HangingTargetContext,
) -> tuple[str | None, str | None] | None:
    if not _is_moved_piece_hanging_after_move(
        context.board_before,
        context.board_after,
        context.user_move,
        context.mover_color,
    ):
        return None
    moved_piece = context.board_after.piece_at(context.user_move.to_square)
    if moved_piece is None:
        moved_piece = context.board_before.piece_at(context.user_move.from_square)
    if moved_piece is None:
        return None
    return _piece_label(moved_piece), chess.square_name(context.user_move.to_square)


def _resolve_opponent_hanging_target(
    context: HangingTargetContext,
) -> tuple[str | None, str | None]:
    if context.hanging_target is None:
        return None, None
    return context.hanging_target.target_piece, context.hanging_target.target_square


def _piece_label(piece: chess.Piece) -> str:
    labels = {
        chess.PAWN: "pawn",
        chess.KNIGHT: "knight",
        chess.BISHOP: "bishop",
        chess.ROOK: "rook",
        chess.QUEEN: "queen",
        chess.KING: "king",
    }
    return labels.get(piece.piece_type, "unknown")
