from __future__ import annotations

from collections.abc import Callable, Iterable

import chess

from tactix.config import Settings
from tactix.const import TIME_CONTROLS
from tactix.detect_tactics__motifs import (
    BaseTacticDetector,
    MotifDetectorSuite,
    build_default_motif_detector_suite,
)
from tactix.format_tactics__explanation import format_tactic_explanation
from tactix.run_stockfish__engine import StockfishEngine
from tactix.utils.logger import get_logger
from tactix.utils.source import normalized_source

logger = get_logger(__name__)
MOTIF_DETECTORS: MotifDetectorSuite = build_default_motif_detector_suite()
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
    source = normalized_source(settings.source)
    profile = _normalized_profile_name(settings, source)
    return source, profile


def _normalized_profile_name(settings: Settings, source: str) -> str:
    if source == "chesscom":
        raw_profile = settings.chesscom_profile or settings.chesscom_time_class
    else:
        raw_profile = settings.lichess_profile or settings.rapid_perf
    return (raw_profile or "").strip().lower()


def _is_profile_in(settings: Settings | None, profiles: Iterable[str]) -> bool:
    """Check if the current profile matches one of the provided profiles.

    Chess.com "daily" is treated as "correspondence" when correspondence is
    part of the requested profile list.
    """
    source, profile = _normalized_profile(settings)
    if not profile:
        return False
    normalized_profiles = _normalized_profiles(profiles)
    if profile in normalized_profiles:
        return True
    return _is_chesscom_daily_match(source, profile, normalized_profiles)


def _normalized_profiles(profiles: Iterable[str]) -> set[str]:
    return {str(item).strip().lower() for item in profiles}


def _is_chesscom_daily_match(source: str, profile: str, normalized_profiles: set[str]) -> bool:
    return source == "chesscom" and "correspondence" in normalized_profiles and profile == "daily"


def _is_fast_profile(settings: Settings | None) -> bool:
    return _is_profile_in(settings, TIME_CONTROLS)


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
    return _is_unclear_two_move_mate(result, best_move, user_move_uci, after_cp, missed_threshold)


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


def _adjust_severity_for_mate(
    severity: float,
    result: str,
    mate_in_one: bool,
    mate_in_two: bool,
    settings: Settings | None,
) -> float:
    if mate_in_one and result == "found":
        return _severity_for_mate_one(severity, settings)
    if mate_in_two and result == "found":
        return _severity_for_mate_two(severity, settings)
    return severity


def _severity_for_mate_one(severity: float, settings: Settings | None) -> float:
    if _is_fast_profile(settings):
        return max(severity, _SEVERITY_MAX)
    return min(severity, _SEVERITY_MIN)


def _severity_for_mate_two(severity: float, settings: Settings | None) -> float:
    if _is_profile_in(settings, TIME_CONTROLS):
        return max(severity, _SEVERITY_MAX)
    return severity


def _adjust_severity_for_fork(severity: float, settings: Settings | None) -> float:
    if _is_profile_in(settings, {"bullet"}):
        severity = max(severity, _SEVERITY_MAX)
    elif _is_profile_in(settings, TIME_CONTROLS):
        severity = min(severity, _SEVERITY_MIN)
    floor = _fork_severity_floor(settings)
    if floor is not None and _is_profile_in(settings, TIME_CONTROLS):
        severity = max(severity, floor)
    return severity


def _adjust_severity_for_pin(severity: float, settings: Settings | None) -> float:
    if _is_profile_in(settings, TIME_CONTROLS):
        return max(severity, _SEVERITY_MAX)
    return severity


def _adjust_severity_for_discovered_check(
    severity: float,
    result: str,
    settings: Settings | None,
) -> float:
    if _is_profile_in(settings, TIME_CONTROLS) and result == "found":
        return min(severity, _SEVERITY_MIN)
    if not _is_profile_in(settings, TIME_CONTROLS) and _is_profile_in(settings, TIME_CONTROLS):
        return min(severity, _SEVERITY_MIN)
    return severity


def _adjust_severity_for_discovered_attack(
    severity: float,
    result: str,
    settings: Settings | None,
) -> float:
    if _is_profile_in(settings, TIME_CONTROLS) and result in {"missed", "failed_attempt"}:
        return max(severity, _SEVERITY_MAX)
    if _is_profile_in(settings, TIME_CONTROLS) and result == "found":
        return min(severity, _SEVERITY_MIN)
    return severity


def _adjust_severity_for_hanging_piece(
    severity: float,
    result: str,
    settings: Settings | None,
) -> float:
    if _is_profile_in(settings, TIME_CONTROLS):
        return min(severity, _SEVERITY_MIN) if result == "found" else max(severity, _SEVERITY_MAX)
    if _is_profile_in(settings, TIME_CONTROLS):
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
    adjuster = _SEVERITY_ADJUSTERS.get(motif)
    if adjuster is None:
        return severity
    return adjuster(severity, result, settings)


def _adjust_fork_wrapper(severity: float, result: str, settings: Settings | None) -> float:
    del result
    return _adjust_severity_for_fork(severity, settings)


def _adjust_pin_wrapper(severity: float, result: str, settings: Settings | None) -> float:
    del result
    return _adjust_severity_for_pin(severity, settings)


def _adjust_discovered_check_wrapper(
    severity: float, result: str, settings: Settings | None
) -> float:
    return _adjust_severity_for_discovered_check(severity, result, settings)


def _adjust_discovered_attack_wrapper(
    severity: float, result: str, settings: Settings | None
) -> float:
    return _adjust_severity_for_discovered_attack(severity, result, settings)


def _adjust_hanging_piece_wrapper(severity: float, result: str, settings: Settings | None) -> float:
    return _adjust_severity_for_hanging_piece(severity, result, settings)


def _adjust_skewer_wrapper(severity: float, result: str, settings: Settings | None) -> float:
    del settings
    return _adjust_severity_for_skewer(severity, result)


_SEVERITY_ADJUSTERS: dict[str, Callable[[float, str, Settings | None], float]] = {
    "fork": _adjust_fork_wrapper,
    "pin": _adjust_pin_wrapper,
    "discovered_check": _adjust_discovered_check_wrapper,
    "discovered_attack": _adjust_discovered_attack_wrapper,
    "hanging_piece": _adjust_hanging_piece_wrapper,
    "skewer": _adjust_skewer_wrapper,
}


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
