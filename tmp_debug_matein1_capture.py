from io import StringIO
from pathlib import Path
import chess
import chess.pgn

from tactix.BaseTacticDetector import BaseTacticDetector

fixture = Path('/Users/andy/tactix/tests/fixtures/matein1.pgn')
chunk = fixture.read_text().strip().split('\n\n\n')[0]
game = chess.pgn.read_game(StringIO(chunk))
fen = game.headers.get('FEN')
board = chess.Board(fen) if fen else game.board()
move = list(game.mainline_moves())[0]
print('capture', board.is_capture(move))
if board.is_capture(move):
    capture_square = move.to_square
    if board.is_en_passant(move):
        capture_square = move.to_square + (-8 if board.turn == chess.WHITE else 8)
    captured = board.piece_at(capture_square)
    print('captured', captured, 'value', BaseTacticDetector.piece_value(captured.piece_type))
    print('undefended', not board.is_attacked_by(not board.turn, capture_square))
