from io import StringIO
from pathlib import Path
import shutil
import chess
import chess.pgn

from tactix.analyze_position import analyze_position
from tactix.config import Settings
from tactix.StockfishEngine import StockfishEngine

fixture = Path('/Users/andy/tactix/tests/fixtures/chesscom_correspondence_sample.pgn')
text = fixture.read_text()
chunk = next(c for c in text.split('\n\n\n') if 'Correspondence Fixture 12 - Hanging Piece High' in c)
game = chess.pgn.read_game(StringIO(chunk))
fen = game.headers.get('FEN')
board = chess.Board(fen) if fen else game.board()
move = list(game.mainline_moves())[0]
settings = Settings(
    source='chesscom',
    chesscom_user='chesscom',
    chesscom_profile='correspondence',
    stockfish_path=Path(shutil.which('stockfish') or 'stockfish'),
    stockfish_movetime_ms=200,
    stockfish_depth=None,
    stockfish_multipv=1,
)
settings.apply_chesscom_profile('correspondence')
with StockfishEngine(settings) as engine:
    tactic_row, outcome_row = analyze_position(
        {
            'game_id': 'debug-hanging-correspondence',
            'position_id': 1,
            'fen': board.fen(),
            'uci': move.uci(),
        },
        engine,
        settings=settings,
    )
print('motif', tactic_row['motif'], 'mate_in', tactic_row.get('mate_in'), 'best_uci', tactic_row.get('best_uci'), 'result', outcome_row['result'])
