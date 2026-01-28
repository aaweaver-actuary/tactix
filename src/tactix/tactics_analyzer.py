from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

import chess

from tactix.config import Settings
from tactix.logging_utils import get_logger
from tactix.stockfish_runner import EngineResult, StockfishEngine
from tactix.tactic_detectors import (
    BaseTacticDetector,
    MotifDetectorSuite,
    build_default_motif_detector_suite,
)
from tactix.tactics_explanation import format_tactic_explanation

logger = get_logger(__name__)
MOTIF_DETECTORS: MotifDetectorSuite = build_default_motif_detector_suite()


def _normalized_profile(settings: Settings | None) -> tuple[str, str]:
    if settings is None:
        return "", ""
    source = (settings.source or "").strip().lower()
    if source == "chesscom":
        profile = (
            (settings.chesscom_profile or settings.chesscom_time_class or "")
            .strip()
            .lower()
        )
    else:
        profile = (
            (settings.lichess_profile or settings.rapid_perf or "").strip().lower()
        )
    return source, profile


def _is_fast_profile(settings: Settings | None) -> bool:
    source, profile = _normalized_profile(settings)
    if not profile:
        return False
    if source == "chesscom":
        return profile in {
            "bullet",
            "blitz",
            "rapid",
            "classical",
            "correspondence",
            "daily",
        }
    return profile in {
        "bullet",
        "blitz",
        "rapid",
        "classical",
        "correspondence",
    }


def _is_bullet_profile(settings: Settings | None) -> bool:
    _, profile = _normalized_profile(settings)
    return profile == "bullet"


def _is_blitz_profile(settings: Settings | None) -> bool:
    _, profile = _normalized_profile(settings)
    return profile == "blitz"


def _is_rapid_profile(settings: Settings | None) -> bool:
    _, profile = _normalized_profile(settings)
    return profile == "rapid"


def _is_classical_profile(settings: Settings | None) -> bool:
    _, profile = _normalized_profile(settings)
    return profile == "classical"


def _is_correspondence_profile(settings: Settings | None) -> bool:
    source, profile = _normalized_profile(settings)
    if not profile:
        return False
    if source == "chesscom":
        return profile in {"correspondence", "daily"}
    return profile == "correspondence"


def _fork_severity_floor(settings: Settings | None) -> float | None:
    if settings is None:
        return None
    return settings.fork_severity_floor


def analyze_position(
    position: Dict[str, object],
    engine: StockfishEngine,
    settings: Settings | None = None,
) -> tuple[Dict[str, object], Dict[str, object]] | None:
    fen = str(position["fen"])
    user_move_uci = str(position["uci"])
    board = chess.Board(fen)
    motif_board = board.copy()
    mover_color = board.turn

    engine_result: EngineResult = engine.analyse(board)
    best_move_obj = engine_result.best_move
    best_move = best_move_obj.uci() if best_move_obj else None
    base_cp = BaseTacticDetector.score_from_pov(
        engine_result.score_cp, mover_color, board.turn
    )
    mate_in_one = False
    mate_in_two = False
    mate_in: int | None = None
    if best_move_obj is not None:
        mate_board = motif_board.copy()
        mate_board.push(best_move_obj)
        mate_in_one = mate_board.is_checkmate()
    if engine_result.mate_in is not None and engine_result.mate_in == 2:
        mate_in_two = True

    try:
        user_move = chess.Move.from_uci(user_move_uci)
    except ValueError:
        logger.warning("Invalid UCI move %s; skipping position", user_move_uci)
        return None

    if user_move not in board.legal_moves:
        logger.warning("Illegal move %s for FEN %s", user_move_uci, fen)
        return None

    board.push(user_move)
    after_cp = BaseTacticDetector.score_from_pov(
        engine.analyse(board).score_cp, mover_color, board.turn
    )

    result, delta = BaseTacticDetector.classify_result(
        best_move, user_move_uci, base_cp, after_cp
    )
    user_board = motif_board.copy()
    user_board.push(user_move)
    if motif_board.is_capture(user_move) and BaseTacticDetector.is_hanging_capture(
        motif_board, user_board, user_move, mover_color
    ):
        motif = "hanging_piece"
    else:
        motif = MOTIF_DETECTORS.infer_motif(motif_board, user_move)
    if mate_in_one:
        mate_in = 1
        if motif != "hanging_piece":
            motif = "mate"
    if mate_in_two:
        mate_in = 2
        motif = "mate"
    severity = abs(delta) / 100.0
    if mate_in_one and result == "found":
        if _is_fast_profile(settings):
            severity = max(severity, 1.5)
        else:
            severity = min(severity, 1.0)
    if mate_in_two and result == "found":
        if (
            _is_bullet_profile(settings)
            or _is_blitz_profile(settings)
            or _is_rapid_profile(settings)
            or _is_classical_profile(settings)
            or _is_correspondence_profile(settings)
        ):
            severity = max(severity, 1.5)
    if motif == "fork":
        if _is_blitz_profile(settings) or _is_rapid_profile(settings):
            severity = min(severity, 1.0)
        if _is_bullet_profile(settings):
            severity = max(severity, 1.5)
        floor = _fork_severity_floor(settings)
        if floor is not None and (
            _is_classical_profile(settings) or _is_correspondence_profile(settings)
        ):
            severity = max(severity, floor)

    if motif == "pin":
        if _is_bullet_profile(settings):
            severity = max(severity, 1.5)
        elif (
            _is_blitz_profile(settings)
            or _is_rapid_profile(settings)
            or _is_classical_profile(settings)
            or _is_correspondence_profile(settings)
        ):
            severity = min(severity, 1.0)

    best_san, explanation = format_tactic_explanation(fen, best_move or "", motif)

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


def analyze_positions(
    positions: Iterable[Dict[str, object]],
    settings: Settings,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    tactics_rows: List[Dict[str, object]] = []
    outcomes_rows: List[Dict[str, object]] = []

    with StockfishEngine(settings) as engine:
        for pos in positions:
            result = analyze_position(pos, engine, settings=settings)
            if result is None:
                continue
            tactic_row, outcome_row = result
            tactics_rows.append(tactic_row)
            outcomes_rows.append(outcome_row)
    return tactics_rows, outcomes_rows
