from tactix._apply_outcome_overrides import _apply_outcome_overrides
from tactix._build_tactic_rows import _build_tactic_rows
from tactix._compare_move__best_line import _compare_move__best_line
from tactix._compute_severity__tactic import (
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
from tactix.StockfishEngine import StockfishEngine


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

    result, delta = BaseTacticDetector.classify_result(best_move, user_move_uci, base_cp, after_cp)
    user_motif = _infer_hanging_or_detected_motif(motif_board, user_move, mover_color)
    motif = user_motif
    best_motif: str | None = None
    if result in {"missed", "failed_attempt", "unclear"} and best_move_obj is not None:
        best_motif = _infer_hanging_or_detected_motif(motif_board, best_move_obj, mover_color)
        motif = _override_motif_for_missed(user_motif, best_motif, result)
    result = _reclassify_failed_attempt(result, delta, motif, user_motif)
    swing = _compare_move__best_line(
        motif_board,
        best_move_obj,
        user_move_uci,
        after_cp,
        engine,
        mover_color,
    )
    result, motif, mate_in = _apply_outcome_overrides(
        result,
        motif,
        best_motif,
        best_move,
        user_move_uci,
        swing,
        after_cp,
        mate_in_one,
        mate_in_two,
        settings,
    )
    severity = _compute_severity__tactic(base_cp, delta, motif, mate_in, result, settings)
    best_san, explanation = format_tactic_explanation(fen, best_move or "", motif)
    return _build_tactic_rows(
        position,
        motif,
        severity,
        best_move,
        base_cp,
        mate_in,
        best_san,
        explanation,
        result,
        user_move_uci,
        delta,
    )
