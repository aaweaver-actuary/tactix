from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

import chess

from tactix.config import Settings
from tactix.logging_utils import get_logger
from tactix.stockfish_runner import EngineResult, StockfishEngine
from tactix.tactics_explanation import format_tactic_explanation

logger = get_logger(__name__)


def _classify_result(
    best_move: str | None, user_move: str, base_cp: int, after_cp: int
) -> tuple[str, int]:
    delta = after_cp - base_cp
    if best_move and user_move == best_move:
        return "found", delta
    if delta <= -300:
        return "missed", delta
    if delta <= -100:
        return "failed_attempt", delta
    return "unclear", delta


def _score_from_pov(score_cp: int, pov_color: bool, turn_color: bool) -> int:
    if turn_color == pov_color:
        return score_cp
    return -score_cp


def _count_high_value_targets(
    board_after: chess.Board, to_square: chess.Square, mover_color: bool
) -> int:
    targets = 0
    for sq in board_after.attacks(to_square):
        piece = board_after.piece_at(sq)
        if (
            piece
            and piece.color != mover_color
            and piece.piece_type
            in (
                chess.QUEEN,
                chess.ROOK,
                chess.BISHOP,
                chess.KNIGHT,
            )
        ):
            targets += 1
    return targets


def _infer_motif(board: chess.Board, best_move: chess.Move | None) -> str:
    if best_move is None:
        return "initiative"

    mover_color = board.turn
    board_after = board.copy()
    board_after.push(best_move)

    if board_after.is_checkmate():
        return "mate"
    if board_after.is_check():
        return "check"

    piece = board.piece_at(best_move.from_square)
    if piece and piece.piece_type == chess.KNIGHT:
        forks = _count_high_value_targets(board_after, best_move.to_square, mover_color)
        if forks >= 2:
            return "fork"

    if board.is_capture(best_move):
        if not board.is_attacked_by(not mover_color, best_move.to_square):
            return "hanging_piece"
        return "capture"

    if board.is_attacked_by(
        not mover_color, best_move.from_square
    ) and not board.is_attacked_by(not mover_color, best_move.to_square):
        return "escape"

    return "initiative"


def _is_fast_profile(settings: Settings | None) -> bool:
    if settings is None:
        return False
    source = (settings.source or "").strip().lower()
    if source == "chesscom":
        profile = (
            settings.chesscom_profile or settings.chesscom_time_class or ""
        ).strip()
        return profile.lower() in {"bullet", "blitz"}
    profile = (settings.lichess_profile or settings.rapid_perf or "").strip()
    return profile.lower() in {"bullet", "blitz"}


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
    base_cp = _score_from_pov(engine_result.score_cp, mover_color, board.turn)
    mate_in_one = False
    if best_move_obj is not None:
        mate_board = motif_board.copy()
        mate_board.push(best_move_obj)
        mate_in_one = mate_board.is_checkmate()

    try:
        user_move = chess.Move.from_uci(user_move_uci)
    except ValueError:
        logger.warning("Invalid UCI move %s; skipping position", user_move_uci)
        return None

    if user_move not in board.legal_moves:
        logger.warning("Illegal move %s for FEN %s", user_move_uci, fen)
        return None

    board.push(user_move)
    after_cp = _score_from_pov(engine.analyse(board).score_cp, mover_color, board.turn)

    result, delta = _classify_result(best_move, user_move_uci, base_cp, after_cp)
    motif = _infer_motif(motif_board, engine_result.best_move)
    severity = abs(delta) / 100.0
    if mate_in_one and result == "found":
        if _is_fast_profile(settings):
            severity = max(severity, 1.5)
        else:
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
