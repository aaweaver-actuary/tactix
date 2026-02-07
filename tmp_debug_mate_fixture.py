from io import StringIO
from pathlib import Path

import chess
import chess.pgn

from tactix.analyze_position import analyze_position
from tactix.config import Settings
from tactix.StockfishEngine import StockfishEngine
from tactix._infer_hanging_or_detected_motif import _infer_hanging_or_detected_motif
from tactix.analyze_tactics__positions import MOTIF_DETECTORS
from tactix.BaseTacticDetector import BaseTacticDetector
import shutil

fixture = Path('/Users/andy/tactix/tests/fixtures/matein2.pgn')
text = fixture.read_text().strip()
chunk = text.split('\n\n\n')[0]
game = chess.pgn.read_game(StringIO(chunk))
fen = game.headers.get('FEN')
board = chess.Board(fen) if fen else game.board()
move = list(game.mainline_moves())[0]
board_after = board.copy(); board_after.push(move)
print('motif', MOTIF_DETECTORS.infer_motif(board, move))
print('infer', _infer_hanging_or_detected_motif(board, move, board.turn))
print('capture', board.is_capture(move), 'hanging', BaseTacticDetector.is_hanging_capture(board, board_after, move, board.turn), 'mate', board_after.is_checkmate())
settings = Settings(stockfish_path=Path(shutil.which('stockfish') or 'stockfish'), stockfish_movetime_ms=60, stockfish_depth=12, stockfish_multipv=1)
with StockfishEngine(settings) as engine:
    result = analyze_position({'game_id': 'debug-mate', 'position_id': 1, 'fen': board.fen(), 'uci': move.uci()}, engine, settings)
print('analyze', result[0]['motif'], 'best_uci', result[0]['best_uci'], 'result', result[1]['result'], 'mate_in', result[0]['mate_in'])
