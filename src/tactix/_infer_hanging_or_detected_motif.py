import chess

from tactix._is_new_hanging_piece import _is_new_hanging_piece
from tactix.analyze_tactics__positions import MOTIF_DETECTORS
from tactix.detect_tactics__motifs import BaseTacticDetector
from tactix.utils.logger import funclogger


@funclogger
def _infer_hanging_or_detected_motif(
    motif_board: chess.Board,
    move: chess.Move,
    mover_color: bool,
) -> str:
    user_board = motif_board.copy()
    user_board.push(move)
    if motif_board.is_capture(move) and BaseTacticDetector.is_hanging_capture(
        motif_board, user_board, move, mover_color
    ):
        return "hanging_piece"
    motif = MOTIF_DETECTORS.infer_motif(motif_board, move)
    if motif == "initiative" and _is_new_hanging_piece(motif_board, user_board, mover_color):
        return "hanging_piece"
    return motif
