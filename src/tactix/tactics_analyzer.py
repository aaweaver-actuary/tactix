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


def _piece_value(piece_type: int) -> int:
    return {
        chess.KING: 10000,
        chess.QUEEN: 900,
        chess.ROOK: 500,
        chess.BISHOP: 300,
        chess.KNIGHT: 300,
        chess.PAWN: 100,
    }.get(piece_type, 0)


def _pinned_squares(board: chess.Board, color: bool) -> set[chess.Square]:
    pinned: set[chess.Square] = set()
    for square, piece in board.piece_map().items():
        if piece.color == color and board.is_pinned(color, square):
            pinned.add(square)
    return pinned


def _first_piece_in_direction(
    board: chess.Board, start: chess.Square, step: int
) -> chess.Square | None:
    file = chess.square_file(start)
    rank = chess.square_rank(start)
    deltas = {
        1: (1, 0),
        -1: (-1, 0),
        8: (0, 1),
        -8: (0, -1),
        9: (1, 1),
        -9: (-1, -1),
        7: (-1, 1),
        -7: (1, -1),
    }
    delta = deltas.get(step)
    if delta is None:
        return None
    df, dr = delta
    file += df
    rank += dr
    while 0 <= file <= 7 and 0 <= rank <= 7:
        square = chess.square(file, rank)
        if board.piece_at(square):
            return square
        file += df
        rank += dr
    return None


def _detect_skewer(board: chess.Board, mover_color: bool) -> bool:
    opponent = not mover_color
    slider_steps = {
        chess.ROOK: (1, -1, 8, -8),
        chess.BISHOP: (7, -7, 9, -9),
        chess.QUEEN: (1, -1, 8, -8, 7, -7, 9, -9),
    }
    for square, piece in board.piece_map().items():
        if piece.color != mover_color or piece.piece_type not in slider_steps:
            continue
        for step in slider_steps[piece.piece_type]:
            first = _first_piece_in_direction(board, square, step)
            if first is None:
                continue
            target = board.piece_at(first)
            if not target or target.color != opponent:
                continue
            second = _first_piece_in_direction(board, first, step)
            if second is None:
                continue
            behind = board.piece_at(second)
            if not behind or behind.color != opponent:
                continue
            if _piece_value(target.piece_type) > _piece_value(behind.piece_type):
                return True
    return False


def _detect_pin(
    board_before: chess.Board,
    board_after: chess.Board,
    best_move: chess.Move,
    mover_color: bool,
) -> bool:
    moved_piece = board_before.piece_at(best_move.from_square)
    if not moved_piece or moved_piece.color != mover_color:
        return False
    slider_steps = {
        chess.ROOK: (1, -1, 8, -8),
        chess.BISHOP: (7, -7, 9, -9),
        chess.QUEEN: (1, -1, 8, -8, 7, -7, 9, -9),
    }
    steps = slider_steps.get(moved_piece.piece_type)
    if not steps:
        return False
    opponent = not mover_color
    start = best_move.to_square
    for step in steps:
        first = _first_piece_in_direction(board_after, start, step)
        if first is None:
            continue
        target = board_after.piece_at(first)
        if not target or target.color != opponent:
            continue
        second = _first_piece_in_direction(board_after, first, step)
        if second is None:
            continue
        behind = board_after.piece_at(second)
        if not behind or behind.color != opponent:
            continue
        if _piece_value(behind.piece_type) > _piece_value(target.piece_type):
            return True
    return False


def _is_hanging_capture(
    board_before: chess.Board,
    board_after: chess.Board,
    best_move: chess.Move,
    mover_color: bool,
) -> bool:
    captured = board_before.piece_at(best_move.to_square)
    if not captured or captured.piece_type not in (
        chess.QUEEN,
        chess.ROOK,
        chess.BISHOP,
        chess.KNIGHT,
    ):
        return False
    if board_after.is_checkmate():
        return True
    opponent = not mover_color
    attackers = list(board_before.attackers(opponent, best_move.to_square))
    if not attackers:
        return True
    return all(board_before.is_pinned(opponent, sq) for sq in attackers)


def _attacked_high_value_targets(
    board: chess.Board, square: chess.Square, opponent: bool
) -> set[chess.Square]:
    targets: set[chess.Square] = set()
    for target_sq in board.attacks(square):
        piece = board.piece_at(target_sq)
        if (
            piece
            and piece.color == opponent
            and piece.piece_type
            in (
                chess.KING,
                chess.QUEEN,
                chess.ROOK,
                chess.BISHOP,
                chess.KNIGHT,
            )
        ):
            targets.add(target_sq)
    return targets


def _detect_discovered_attack(
    board_before: chess.Board,
    board_after: chess.Board,
    best_move: chess.Move,
    mover_color: bool,
) -> bool:
    moved_piece = board_before.piece_at(best_move.from_square)
    slider_types = {chess.ROOK, chess.BISHOP, chess.QUEEN}
    opponent = not mover_color
    for square, piece in board_after.piece_map().items():
        if piece.color != mover_color or piece.piece_type not in slider_types:
            continue
        if moved_piece and moved_piece.piece_type in slider_types:
            if square == best_move.to_square:
                continue
        piece_before = board_before.piece_at(square)
        if not piece_before or piece_before.color != mover_color:
            continue
        before_targets = _attacked_high_value_targets(board_before, square, opponent)
        after_targets = _attacked_high_value_targets(board_after, square, opponent)
        if after_targets - before_targets:
            return True
    return False


def _infer_motif(board: chess.Board, best_move: chess.Move | None) -> str:
    if best_move is None:
        return "initiative"

    mover_color = board.turn
    board_after = board.copy()
    board_after.push(best_move)
    is_checkmate = board_after.is_checkmate()

    if _detect_discovered_attack(board, board_after, best_move, mover_color):
        return "discovered_attack"

    if _detect_skewer(board_after, mover_color):
        return "skewer"

    if board.is_capture(best_move) and _is_hanging_capture(
        board, board_after, best_move, mover_color
    ):
        return "hanging_piece"

    if _detect_pin(board, board_after, best_move, mover_color):
        return "pin"

    piece = board.piece_at(best_move.from_square)
    if piece and piece.piece_type in (
        chess.QUEEN,
        chess.ROOK,
        chess.BISHOP,
        chess.KNIGHT,
    ):
        forks = _count_high_value_targets(board_after, best_move.to_square, mover_color)
        if forks >= 2:
            return "fork"
        if forks >= 1 and board_after.is_check():
            return "fork"

    if board.is_capture(best_move):
        return "capture"

    if is_checkmate:
        return "mate"

    if board_after.is_check():
        return "check"

    if board.is_attacked_by(
        not mover_color, best_move.from_square
    ) and not board.is_attacked_by(not mover_color, best_move.to_square):
        return "escape"

    return "initiative"


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
    after_cp = _score_from_pov(engine.analyse(board).score_cp, mover_color, board.turn)

    result, delta = _classify_result(best_move, user_move_uci, base_cp, after_cp)
    user_board = motif_board.copy()
    user_board.push(user_move)
    if motif_board.is_capture(user_move) and _is_hanging_capture(
        motif_board, user_board, user_move, mover_color
    ):
        motif = "hanging_piece"
    else:
        motif = _infer_motif(motif_board, user_move)
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
