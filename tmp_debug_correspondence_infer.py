import logging
from io import StringIO
from pathlib import Path
import chess
import chess.pgn

from tactix._infer_hanging_or_detected_motif import _infer_hanging_or_detected_motif
from tactix.analyze_tactics__positions import MOTIF_DETECTORS

logging.disable(logging.CRITICAL)

fixture = Path('/Users/andy/tactix/tests/fixtures/chesscom_correspondence_sample.pgn')
text = fixture.read_text()
chunk = next(c for c in text.split('\n\n\n') if 'Correspondence Fixture 12 - Hanging Piece High' in c)
game = chess.pgn.read_game(StringIO(chunk))
fen = game.headers.get('FEN')
board = chess.Board(fen) if fen else game.board()
move = list(game.mainline_moves())[0]
board_after = board.copy(); board_after.push(move)
print('motif', MOTIF_DETECTORS.infer_motif(board, move))
print('infer', _infer_hanging_or_detected_motif(board, move, board.turn))
print('capture', board.is_capture(move), 'checkmate', board_after.is_checkmate())
