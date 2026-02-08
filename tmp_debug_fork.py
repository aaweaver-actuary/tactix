import shutil
from pathlib import Path
import chess
from tactix.config import Settings
from tactix.StockfishEngine import StockfishEngine
from tactix.pgn_utils import split_pgn_chunks
from tests.fixture_helpers import find_missed_position

def main():
    fixture_path = Path('tests/fixtures/chesscom_rapid_sample.pgn')
    chunks = split_pgn_chunks(fixture_path.read_text())
    fork_pgn = next(chunk for chunk in chunks if 'Rapid Fixture 5' in chunk)
    game = chess.pgn.read_game(io := __import__('io').StringIO(fork_pgn))
    board = game.board()
    move = next(iter(game.mainline_moves()))
    position = {
        'game_id': 'rapid-fork',
        'user': 'chesscom',
        'source': 'chesscom',
        'fen': board.fen(),
        'ply': board.ply(),
        'move_number': board.fullmove_number,
        'side_to_move': 'black' if board.turn == chess.BLACK else 'white',
        'uci': move.uci(),
        'san': board.san(move),
        'clock_seconds': None,
        'is_legal': True,
    }
    settings = Settings(
        source='chesscom',
        chesscom_user='chesscom',
        chesscom_profile='rapid',
        stockfish_path=Path(shutil.which('stockfish') or 'stockfish'),
        stockfish_movetime_ms=60,
        stockfish_depth=None,
        stockfish_multipv=1,
    )
    settings.apply_chesscom_profile('rapid')
    with StockfishEngine(settings) as engine:
        try:
            missed_position, result = find_missed_position(position, engine, settings, 'fork')
        except AssertionError as exc:
            print('error', exc)
            return
    tactic_row, outcome_row = result
    print('tactic', tactic_row)
    print('outcome', outcome_row)

if __name__ == '__main__':
    main()
