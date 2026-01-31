from __future__ import annotations

from collections.abc import Iterable

import chess

from tactix.config import Settings
from tactix.detect_tactics__motifs import (
    BaseTacticDetector,
    MotifDetectorSuite,
    build_default_motif_detector_suite,
)
from tactix.format_tactics__explanation import format_tactic_explanation
from tactix.stockfish_engine import StockfishEngine
from tactix.utils import Logger

logger = Logger(__name__)


MOTIF_DETECTORS: MotifDetectorSuite = build_default_motif_detector_suite()
_FAILED_ATTEMPT_RECLASSIFY_THRESHOLDS = {
    "discovered_attack": -1200,
    "discovered_check": -950,
    "fork": -500,
    "hanging_piece": -900,
    "skewer": -700,
}
_PIN_FAILED_ATTEMPT_SWING_THRESHOLD = -50
_SKEWER_FAILED_ATTEMPT_SWING_THRESHOLD = -50
_DISCOVERED_ATTACK_FAILED_ATTEMPT_SWING_THRESHOLD = -50
_DISCOVERED_CHECK_FAILED_ATTEMPT_SWING_THRESHOLD = -50
_HANGING_PIECE_FAILED_ATTEMPT_SWING_THRESHOLD = -50
_MATE_MISSED_SCORE_MULTIPLIER = 200
_SEVERITY_MIN = 1.0
_SEVERITY_MAX = 1.5
_OVERRIDEABLE_USER_MOTIFS = {"initiative", "capture", "check", "escape"}
_MISSED_OVERRIDE_TARGETS = {
    "mate",
    "fork",
    "pin",
    "skewer",
    "discovered_attack",
    "discovered_check",
    "hanging_piece",
}
_FAILED_ATTEMPT_OVERRIDE_TARGETS = {
    "mate",
    "fork",
    "pin",
    "skewer",
    "discovered_attack",
    "discovered_check",
    "hanging_piece",
}
MATE_IN_ONE = 1
MATE_IN_TWO = 2
_MATE_IN_ONE_UNCLEAR_SCORE_THRESHOLD = _MATE_MISSED_SCORE_MULTIPLIER * MATE_IN_ONE + 50


def _is_profile_in(settings: Settings, profiles: set[str]) -> bool:
    normalized = _normalize_profile__settings(settings)
    if not normalized:
        return False
    return normalized in {entry.strip().lower() for entry in profiles}


def _normalize_profile__settings(settings: Settings) -> str:
    profile_value = _resolve_profile_value__settings(settings)
    return profile_value.strip().lower()


def _resolve_profile_value__settings(settings: Settings) -> str:
    if settings.source == "chesscom":
        return _resolve_chesscom_profile_value(settings)
    return settings.lichess_profile or settings.rapid_perf


def _resolve_chesscom_profile_value(settings: Settings) -> str:
    profile_value = settings.chesscom_profile or settings.chesscom.time_class
    if profile_value == "daily":
        return "correspondence"
    return profile_value


def _fork_severity_floor(settings: Settings | None) -> float | None:
    """Returns the fork severity floor from settings, if applicable.

    Parameters
    ----------
    settings : Settings or None
        The settings object to check, or None.

    Returns
    -------
    float or None
        The fork severity floor if defined in settings and applicable, otherwise None.
    """
    if settings is None:
        return None
    return settings.fork_severity_floor


def _compute_severity__tactic(
    base_cp: int,
    delta: int,
    motif: str,
    mate_in: int | None,
    result: str,
    settings: Settings | None,
) -> float:
    severity = _severity_for_result(base_cp, delta, motif, mate_in, result)
    severity = min(severity, _SEVERITY_MAX)
    return _apply_fork_severity_floor(severity, motif, settings)


def _severity_for_found_tactic(
    base_cp: int,
    delta: int,
    motif: str,
    mate_in: int | None,
) -> float:
    if mate_in in {MATE_IN_ONE, MATE_IN_TWO} or motif == "mate":
        return _SEVERITY_MAX
    if motif == "pin":
        return abs(base_cp) / 100.0
    return max(abs(delta) / 100.0, 0.01)


def _severity_for_result(
    base_cp: int,
    delta: int,
    motif: str,
    mate_in: int | None,
    result: str,
) -> float:
    if result == "found":
        return _severity_for_found_tactic(base_cp, delta, motif, mate_in)
    return _severity_for_nonfound_tactic(base_cp, delta, motif)


def _severity_for_nonfound_tactic(base_cp: int, delta: int, motif: str) -> float:
    if motif == "discovered_check":
        return abs(delta) / 100.0
    return max(abs(base_cp), abs(delta)) / 100.0


def _apply_fork_severity_floor(
    severity: float,
    motif: str,
    settings: Settings | None,
) -> float:
    if motif != "fork":
        return severity
    floor = _fork_floor_for_settings(settings)
    if floor is None:
        return severity
    return max(severity, floor)


def _fork_floor_for_settings(settings: Settings | None) -> float | None:
    floor = _fork_severity_floor(settings)
    if floor is not None or settings is None:
        return floor
    if _is_profile_in(settings, {"bullet"}):
        return _SEVERITY_MAX
    return None


def _evaluate_engine_position(
    board: chess.Board,
    engine: StockfishEngine,
    mover_color: bool,
    motif_board: chess.Board,
) -> tuple[chess.Move | None, str | None, int, bool, bool]:
    engine_result = engine.analyse(board)
    best_move_obj = engine_result.best_move
    best_move = best_move_obj.uci() if best_move_obj else None
    base_cp = BaseTacticDetector.score_from_pov(engine_result.score_cp, mover_color, board.turn)
    mate_in_one = False
    mate_in_two = False
    if best_move_obj is not None:
        mate_board = motif_board.copy()
        mate_board.push(best_move_obj)
        mate_in_one = mate_board.is_checkmate()
    if engine_result.mate_in is not None and engine_result.mate_in == MATE_IN_TWO:
        mate_in_two = True
    return best_move_obj, best_move, base_cp, mate_in_one, mate_in_two


def _prepare_position_inputs(
    position: dict[str, object],
) -> tuple[str, str, chess.Board, chess.Board, bool]:
    fen = str(position["fen"])
    user_move_uci = str(position["uci"])
    board = chess.Board(fen)
    motif_board = board.copy()
    mover_color = board.turn
    return fen, user_move_uci, board, motif_board, mover_color


def _build_tactic_rows(
    position: dict[str, object],
    motif: str,
    severity: float,
    best_move: str | None,
    base_cp: int,
    mate_in: int | None,
    best_san: str | None,
    explanation: str | None,
    result: str,
    user_move_uci: str,
    delta: int,
) -> tuple[dict[str, object], dict[str, object]]:
    tactic_row = {
        "game_id": position["game_id"],
        "position_id": position.get("position_id"),
        "motif": motif,
        "severity": severity,
        "best_uci": best_move or "",
        "eval_cp": base_cp,
        "best_san": best_san,
        "explanation": explanation,
        "mate_in": mate_in,
    }
    outcome_row = {
        "tactic_id": None,  # filled by caller
        "result": result,
        "user_uci": user_move_uci,
        "eval_delta": delta,
    }
    return tactic_row, outcome_row


def _parse_user_move(board: chess.Board, user_move_uci: str, fen: str) -> chess.Move | None:
    try:
        user_move = chess.Move.from_uci(user_move_uci)
    except ValueError:
        logger.warning("Invalid UCI move %s; skipping position", user_move_uci)
        return None
    if user_move not in board.legal_moves:
        logger.warning("Illegal move %s for FEN %s", user_move_uci, fen)
        return None
    return user_move


def _score_after_move(board: chess.Board, engine: StockfishEngine, mover_color: bool) -> int:
    return BaseTacticDetector.score_from_pov(
        engine.analyse(board).score_cp, mover_color, board.turn
    )


def _score_best_line__after_move(
    board: chess.Board,
    best_move: chess.Move | None,
    engine: StockfishEngine,
    mover_color: bool,
) -> int | None:
    if best_move is None:
        return None
    best_board = board.copy()
    best_board.push(best_move)
    return _score_after_move(best_board, engine, mover_color)


def _compare_move__best_line(
    board: chess.Board,
    best_move: chess.Move | None,
    user_move_uci: str,
    after_cp: int,
    engine: StockfishEngine,
    mover_color: bool,
) -> int | None:
    if best_move is None or user_move_uci == best_move.uci():
        return None
    best_after_cp = _score_best_line__after_move(board, best_move, engine, mover_color)
    if best_after_cp is None:
        return None
    return after_cp - best_after_cp


def _infer_hanging_or_detected_motif(
    motif_board: chess.Board,
    move: chess.Move,
    mover_color: bool,
) -> str:
    if motif_board.is_capture(move):
        user_board = motif_board.copy()
        user_board.push(move)
        if BaseTacticDetector.is_hanging_capture(motif_board, user_board, move, mover_color):
            return "hanging_piece"
    return MOTIF_DETECTORS.infer_motif(motif_board, move)


def _override_motif_for_missed(
    user_motif: str,
    best_motif: str | None,
    result: str,
) -> str:
    if not _should_override_motif(user_motif, best_motif, result):
        return user_motif
    return best_motif or user_motif


def _should_override_motif(user_motif: str, best_motif: str | None, result: str) -> bool:
    if user_motif not in _OVERRIDEABLE_USER_MOTIFS:
        return False
    if result == "missed":
        return bool(best_motif in _MISSED_OVERRIDE_TARGETS)
    if result == "failed_attempt":
        return bool(best_motif in _FAILED_ATTEMPT_OVERRIDE_TARGETS)
    return False


def _reclassify_failed_attempt(result: str, delta: int, motif: str, user_motif: str) -> str:
    reclassify_motif = _reclassify_motif(motif, user_motif)
    if not _should_reclassify(result, delta, reclassify_motif):
        return result
    return "failed_attempt"


def _reclassify_motif(motif: str, user_motif: str) -> str | None:
    if user_motif in _FAILED_ATTEMPT_RECLASSIFY_THRESHOLDS:
        return user_motif
    if motif in _FAILED_ATTEMPT_RECLASSIFY_THRESHOLDS and motif != "discovered_attack":
        return motif
    return None


def _should_reclassify(result: str, delta: int, reclassify_motif: str | None) -> bool:
    if result != "missed" or reclassify_motif is None:
        return False
    return delta > _FAILED_ATTEMPT_RECLASSIFY_THRESHOLDS[reclassify_motif]


def _compute_eval__swing_threshold(motif: str, settings: Settings | None) -> int | None:
    del settings
    thresholds = {
        "pin": _PIN_FAILED_ATTEMPT_SWING_THRESHOLD,
        "skewer": _SKEWER_FAILED_ATTEMPT_SWING_THRESHOLD,
        "discovered_attack": _DISCOVERED_ATTACK_FAILED_ATTEMPT_SWING_THRESHOLD,
        "discovered_check": _DISCOVERED_CHECK_FAILED_ATTEMPT_SWING_THRESHOLD,
        "hanging_piece": _HANGING_PIECE_FAILED_ATTEMPT_SWING_THRESHOLD,
    }
    return thresholds.get(motif)


def _select_motif__pin_target(motif: str, best_motif: str | None) -> str:
    if best_motif == "pin":
        return "pin"
    if motif == "pin":
        return "pin"
    return ""


def _select_motif__skewer_target(motif: str, best_motif: str | None) -> str:
    if best_motif == "skewer":
        return "skewer"
    if motif == "skewer":
        return "skewer"
    return ""


def _select_motif__discovered_attack_target(motif: str, best_motif: str | None) -> str:
    if best_motif == "discovered_attack":
        return "discovered_attack"
    if motif == "discovered_attack":
        return "discovered_attack"
    return ""


def _select_motif__discovered_check_target(motif: str, best_motif: str | None) -> str:
    if best_motif == "discovered_check":
        return "discovered_check"
    if motif == "discovered_check":
        return "discovered_check"
    return ""


def _select_motif__hanging_piece_target(motif: str, best_motif: str | None) -> str:
    if best_motif == "hanging_piece":
        return "hanging_piece"
    if motif == "hanging_piece":
        return "hanging_piece"
    return ""


def _should_override__pin_failed_attempt(
    result: str,
    swing: int | None,
    threshold: int | None,
    target_motif: str,
) -> bool:
    return bool(
        result == "unclear"
        and swing is not None
        and threshold is not None
        and swing <= threshold
        and target_motif
    )


def _should_override__skewer_failed_attempt(
    result: str,
    swing: int | None,
    threshold: int | None,
    target_motif: str,
) -> bool:
    return bool(
        result == "unclear"
        and swing is not None
        and threshold is not None
        and swing <= threshold
        and target_motif
    )


def _should_override__discovered_attack_failed_attempt(
    result: str,
    swing: int | None,
    threshold: int | None,
    target_motif: str,
) -> bool:
    return bool(
        result == "unclear"
        and swing is not None
        and threshold is not None
        and swing <= threshold
        and target_motif
    )


def _should_override__discovered_check_failed_attempt(
    result: str,
    swing: int | None,
    threshold: int | None,
    target_motif: str,
) -> bool:
    return bool(
        result == "unclear"
        and swing is not None
        and threshold is not None
        and swing <= threshold
        and target_motif
    )


def _should_override__hanging_piece_failed_attempt(
    result: str,
    swing: int | None,
    threshold: int | None,
    target_motif: str,
) -> bool:
    return bool(
        result == "unclear"
        and swing is not None
        and threshold is not None
        and swing <= threshold
        and target_motif
    )


def _apply_outcome__failed_attempt_pin(
    result: str,
    motif: str,
    best_motif: str | None,
    swing: int | None,
    threshold: int | None,
) -> tuple[str, str]:
    target_motif = _select_motif__pin_target(motif, best_motif)
    if _should_override__pin_failed_attempt(result, swing, threshold, target_motif):
        return "failed_attempt", target_motif
    return result, motif


def _apply_outcome__failed_attempt_skewer(
    result: str,
    motif: str,
    best_motif: str | None,
    swing: int | None,
    threshold: int | None,
) -> tuple[str, str]:
    target_motif = _select_motif__skewer_target(motif, best_motif)
    if _should_override__skewer_failed_attempt(result, swing, threshold, target_motif):
        return "failed_attempt", target_motif
    return result, motif


def _apply_outcome__failed_attempt_discovered_attack(
    result: str,
    motif: str,
    best_motif: str | None,
    swing: int | None,
    threshold: int | None,
) -> tuple[str, str]:
    target_motif = _select_motif__discovered_attack_target(motif, best_motif)
    if _should_override__discovered_attack_failed_attempt(result, swing, threshold, target_motif):
        return "failed_attempt", target_motif
    return result, motif


def _apply_outcome__failed_attempt_discovered_check(
    result: str,
    motif: str,
    best_motif: str | None,
    swing: int | None,
    threshold: int | None,
) -> tuple[str, str]:
    target_motif = _select_motif__discovered_check_target(motif, best_motif)
    if _should_override__discovered_check_failed_attempt(result, swing, threshold, target_motif):
        return "failed_attempt", target_motif
    return result, motif


def _apply_outcome__failed_attempt_hanging_piece(
    result: str,
    motif: str,
    best_motif: str | None,
    swing: int | None,
    threshold: int | None,
) -> tuple[str, str]:
    target_motif = _select_motif__hanging_piece_target(motif, best_motif)
    if _should_override__hanging_piece_failed_attempt(result, swing, threshold, target_motif):
        return "failed_attempt", target_motif
    return result, motif


def _apply_outcome__failed_attempt_line_tactics(
    result: str,
    motif: str,
    best_motif: str | None,
    swing: int | None,
    settings: Settings | None,
) -> tuple[str, str]:
    result, motif = _apply_outcome__failed_attempt_pin(
        result, motif, best_motif, swing, _compute_eval__swing_threshold("pin", settings)
    )
    result, motif = _apply_outcome__failed_attempt_skewer(
        result,
        motif,
        best_motif,
        swing,
        _compute_eval__swing_threshold("skewer", settings),
    )
    result, motif = _apply_outcome__failed_attempt_discovered_attack(
        result,
        motif,
        best_motif,
        swing,
        _compute_eval__swing_threshold("discovered_attack", settings),
    )
    return _apply_outcome__failed_attempt_discovered_check(
        result,
        motif,
        best_motif,
        swing,
        _compute_eval__swing_threshold("discovered_check", settings),
    )


def _apply_mate_overrides(
    result: str,
    motif: str,
    best_move: str | None,
    user_move_uci: str,
    after_cp: int,
    mate_in_one: bool,
    mate_in_two: bool,
) -> tuple[str, str, int | None]:
    mate_in = _resolve_mate_in(mate_in_one, mate_in_two)
    motif = _override_mate_motif(motif, mate_in)
    result = _apply_outcome__unclear_mate_in_one(
        result,
        best_move,
        user_move_uci,
        after_cp,
        mate_in,
    )
    if _should_upgrade_mate_result(
        result,
        best_move,
        user_move_uci,
        after_cp,
        mate_in,
    ):
        result = "failed_attempt"
    return result, motif, mate_in


def _resolve_mate_in(mate_in_one: bool, mate_in_two: bool) -> int | None:
    if mate_in_two:
        return MATE_IN_TWO
    if mate_in_one:
        return MATE_IN_ONE
    return None


def _override_mate_motif(motif: str, mate_in: int | None) -> str:
    if mate_in == MATE_IN_TWO:
        return "mate"
    if mate_in == MATE_IN_ONE and motif != "hanging_piece":
        return "mate"
    return motif


def _should_upgrade_mate_result(
    result: str,
    best_move: str | None,
    user_move_uci: str,
    after_cp: int,
    mate_in: int | None,
) -> bool:
    if mate_in not in {MATE_IN_ONE, MATE_IN_TWO}:
        return False
    missed_threshold = _MATE_MISSED_SCORE_MULTIPLIER * mate_in
    if _is_missed_mate(result, after_cp, missed_threshold):
        return True
    if mate_in == MATE_IN_TWO:
        return _is_unclear_two_move_mate(
            result, best_move, user_move_uci, after_cp, missed_threshold
        )
    return False


def _is_missed_mate(result: str, after_cp: int, threshold: int) -> bool:
    return result == "missed" and after_cp >= threshold


def _is_unclear_two_move_mate(
    result: str,
    best_move: str | None,
    user_move_uci: str,
    after_cp: int,
    threshold: int,
) -> bool:
    if result != "unclear" or best_move is None:
        return False
    return user_move_uci != best_move and after_cp >= threshold


def _apply_outcome__unclear_mate_in_one(
    result: str,
    best_move: str | None,
    user_move_uci: str,
    after_cp: int,
    mate_in: int | None,
) -> str:
    if _should_mark_unclear_mate_in_one(
        result,
        best_move,
        user_move_uci,
        after_cp,
        mate_in,
    ):
        return "unclear"
    return result


def _should_mark_unclear_mate_in_one(
    result: str,
    best_move: str | None,
    user_move_uci: str,
    after_cp: int,
    mate_in: int | None,
) -> bool:
    return bool(
        mate_in == MATE_IN_ONE
        and best_move is not None
        and user_move_uci != best_move
        and result in {"missed", "failed_attempt"}
        and after_cp >= _MATE_IN_ONE_UNCLEAR_SCORE_THRESHOLD
    )


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
    result, motif = _apply_outcome__failed_attempt_line_tactics(
        result, motif, best_motif, swing, settings
    )
    result, motif = _apply_outcome__failed_attempt_hanging_piece(
        result,
        motif,
        best_motif,
        swing,
        _compute_eval__swing_threshold("hanging_piece", settings),
    )
    result, motif, mate_in = _apply_mate_overrides(
        result,
        motif,
        best_move,
        user_move_uci,
        after_cp,
        mate_in_one,
        mate_in_two,
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


def analyze_positions(
    positions: Iterable[dict[str, object]],
    settings: Settings,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    tactics_rows: list[dict[str, object]] = []
    outcomes_rows: list[dict[str, object]] = []

    with StockfishEngine(settings) as engine:
        for pos in positions:
            result = analyze_position(pos, engine, settings=settings)
            if result is None:
                continue
            tactic_row, outcome_row = result
            tactics_rows.append(tactic_row)
            outcomes_rows.append(outcome_row)
    return tactics_rows, outcomes_rows
