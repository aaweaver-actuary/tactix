from __future__ import annotations

from collections.abc import Iterable

import chess

from tactix.config import Settings
from tactix.logging_utils import get_logger
from tactix.stockfish_runner import StockfishEngine
from tactix.tactic_detectors import (
    BaseTacticDetector,
    MotifDetectorSuite,
    build_default_motif_detector_suite,
)
from tactix.tactics_explanation import format_tactic_explanation

logger = get_logger(__name__)
MOTIF_DETECTORS: MotifDetectorSuite = build_default_motif_detector_suite()
_PROFILE_FAST = frozenset({"bullet", "blitz", "rapid", "classical", "correspondence"})
_PROFILE_DISCOVERED_CHECK_LOW = frozenset(
    {"bullet", "blitz", "rapid", "classical", "correspondence"}
)
_PROFILE_DISCOVERED_CHECK_HIGH = frozenset({"blitz", "rapid", "classical", "correspondence"})
_PROFILE_DISCOVERED_ATTACK_LOW = frozenset()
_PROFILE_DISCOVERED_ATTACK_HIGH = frozenset(
    {"bullet", "blitz", "rapid", "classical", "correspondence"}
)
_PROFILE_HANGING_PIECE_LOW = frozenset()
_PROFILE_HANGING_PIECE_HIGH = frozenset({"bullet", "blitz", "rapid", "classical", "correspondence"})
_PROFILE_FORK_LOW = frozenset({"blitz", "rapid"})
_PROFILE_FORK_HIGH = frozenset({"bullet"})
_PROFILE_FORK_SLOW = frozenset({"classical", "correspondence"})
_FAILED_ATTEMPT_RECLASSIFY_THRESHOLDS = {
    "discovered_attack": -1200,
    "discovered_check": -950,
    "fork": -500,
    "skewer": -700,
}
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
}
MATE_IN_ONE = 1
MATE_IN_TWO = 2


def _normalized_profile(settings: Settings | None) -> tuple[str, str]:
    if settings is None:
        return "", ""
    source = (settings.source or "").strip().lower()
    if source == "chesscom":
        profile = (settings.chesscom_profile or settings.chesscom_time_class or "").strip().lower()
    else:
        profile = (settings.lichess_profile or settings.rapid_perf or "").strip().lower()
    return source, profile


def _is_profile_in(settings: Settings | None, profiles: Iterable[str]) -> bool:
    """Check if the current profile matches one of the provided profiles.

    Chess.com "daily" is treated as "correspondence" when correspondence is
    part of the requested profile list.
    """
    source, profile = _normalized_profile(settings)
    if not profile:
        return False
    normalized_profiles = {str(item).strip().lower() for item in profiles}
    if profile in normalized_profiles:
        return True
    if source == "chesscom" and "correspondence" in normalized_profiles:
        return profile == "daily"
    return False


def _is_fast_profile(settings: Settings | None) -> bool:
    return _is_profile_in(settings, _PROFILE_FAST)


def _fork_severity_floor(settings: Settings | None) -> float | None:
    if settings is None:
        return None
    return settings.fork_severity_floor


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
    if user_motif in _OVERRIDEABLE_USER_MOTIFS and (
        (result == "missed" and best_motif in _MISSED_OVERRIDE_TARGETS)
        or (result == "failed_attempt" and best_motif in _FAILED_ATTEMPT_OVERRIDE_TARGETS)
    ):
        return best_motif or user_motif
    return user_motif


def _reclassify_failed_attempt(result: str, delta: int, motif: str, user_motif: str) -> str:
    reclassify_motif = user_motif if user_motif in _FAILED_ATTEMPT_RECLASSIFY_THRESHOLDS else None
    if (
        reclassify_motif is None
        and motif in _FAILED_ATTEMPT_RECLASSIFY_THRESHOLDS
        and motif != "discovered_attack"
    ):
        reclassify_motif = motif
    if (
        result == "missed"
        and reclassify_motif is not None
        and delta > _FAILED_ATTEMPT_RECLASSIFY_THRESHOLDS[reclassify_motif]
    ):
        return "failed_attempt"
    return result


def _apply_mate_overrides(
    result: str,
    motif: str,
    best_move: str | None,
    user_move_uci: str,
    after_cp: int,
    mate_in_one: bool,
    mate_in_two: bool,
) -> tuple[str, str, int | None]:
    mate_in: int | None = None
    if mate_in_one:
        mate_in = MATE_IN_ONE
        if motif != "hanging_piece":
            motif = "mate"
    if mate_in_two:
        mate_in = MATE_IN_TWO
        motif = "mate"
    if mate_in in {MATE_IN_ONE, MATE_IN_TWO}:
        missed_threshold = _MATE_MISSED_SCORE_MULTIPLIER * mate_in
        if (result == "missed" and after_cp >= missed_threshold) or (
            mate_in == MATE_IN_TWO
            and result == "unclear"
            and best_move
            and user_move_uci != best_move
            and after_cp >= missed_threshold
        ):
            result = "failed_attempt"
    return result, motif, mate_in


def _adjust_severity_for_mate(
    severity: float,
    result: str,
    mate_in_one: bool,
    mate_in_two: bool,
    settings: Settings | None,
) -> float:
    if mate_in_one and result == "found":
        return (
            max(severity, _SEVERITY_MAX)
            if _is_fast_profile(settings)
            else min(severity, _SEVERITY_MIN)
        )
    if mate_in_two and result == "found" and _is_profile_in(settings, _PROFILE_FAST):
        return max(severity, _SEVERITY_MAX)
    return severity


def _adjust_severity_for_fork(severity: float, settings: Settings | None) -> float:
    if _is_profile_in(settings, _PROFILE_FORK_LOW):
        severity = min(severity, _SEVERITY_MIN)
    if _is_profile_in(settings, _PROFILE_FORK_HIGH):
        severity = max(severity, _SEVERITY_MAX)
    floor = _fork_severity_floor(settings)
    if floor is not None and _is_profile_in(settings, _PROFILE_FORK_SLOW):
        severity = max(severity, floor)
    return severity


def _adjust_severity_for_pin(severity: float, settings: Settings | None) -> float:
    if _is_profile_in(settings, _PROFILE_FAST):
        return max(severity, _SEVERITY_MAX)
    return severity


def _adjust_severity_for_discovered_check(
    severity: float,
    result: str,
    settings: Settings | None,
) -> float:
    if _is_profile_in(settings, _PROFILE_DISCOVERED_CHECK_HIGH) and result == "found":
        return min(severity, _SEVERITY_MIN)
    if not _is_profile_in(settings, _PROFILE_DISCOVERED_CHECK_HIGH) and _is_profile_in(
        settings, _PROFILE_DISCOVERED_CHECK_LOW
    ):
        return min(severity, _SEVERITY_MIN)
    return severity


def _adjust_severity_for_discovered_attack(
    severity: float,
    result: str,
    settings: Settings | None,
) -> float:
    if _is_profile_in(settings, _PROFILE_DISCOVERED_ATTACK_LOW):
        return min(severity, _SEVERITY_MIN)
    if _is_profile_in(settings, _PROFILE_DISCOVERED_ATTACK_HIGH) and result == "found":
        return min(severity, _SEVERITY_MIN)
    return severity


def _adjust_severity_for_hanging_piece(
    severity: float,
    result: str,
    settings: Settings | None,
) -> float:
    if _is_profile_in(settings, _PROFILE_HANGING_PIECE_HIGH):
        return min(severity, _SEVERITY_MIN) if result == "found" else max(severity, _SEVERITY_MAX)
    if _is_profile_in(settings, _PROFILE_HANGING_PIECE_LOW):
        return min(severity, _SEVERITY_MIN)
    return severity


def _adjust_severity_for_skewer(severity: float, result: str) -> float:
    if result == "found":
        return min(severity, _SEVERITY_MIN)
    return severity


def _adjust_severity(
    severity: float,
    motif: str,
    result: str,
    mate_in_one: bool,
    mate_in_two: bool,
    settings: Settings | None,
) -> float:
    severity = _adjust_severity_for_mate(severity, result, mate_in_one, mate_in_two, settings)
    if motif == "fork":
        severity = _adjust_severity_for_fork(severity, settings)
    elif motif == "pin":
        severity = _adjust_severity_for_pin(severity, settings)
    elif motif == "discovered_check":
        severity = _adjust_severity_for_discovered_check(severity, result, settings)
    elif motif == "discovered_attack":
        severity = _adjust_severity_for_discovered_attack(severity, result, settings)
    elif motif == "hanging_piece":
        severity = _adjust_severity_for_hanging_piece(severity, result, settings)
    elif motif == "skewer":
        severity = _adjust_severity_for_skewer(severity, result)
    return severity


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
    if result in {"missed", "failed_attempt"} and best_move_obj is not None:
        best_motif = _infer_hanging_or_detected_motif(motif_board, best_move_obj, mover_color)
        motif = _override_motif_for_missed(user_motif, best_motif, result)
    result = _reclassify_failed_attempt(result, delta, motif, user_motif)
    result, motif, mate_in = _apply_mate_overrides(
        result,
        motif,
        best_move,
        user_move_uci,
        after_cp,
        mate_in_one,
        mate_in_two,
    )
    severity = abs(delta) / 100.0
    severity = _adjust_severity(
        severity,
        motif,
        result,
        mate_in_one,
        mate_in_two,
        settings,
    )

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
