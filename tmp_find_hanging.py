import chess
import chess.pgn
from io import StringIO
from pathlib import Path
from tests.test_api_chesscom_bullet_pipeline_canonical import _hanging_user_piece_labels_after_move

def main():
    text = Path('tests/fixtures/chesscom_2_bullet_games.pgn').read_text()
    bio = StringIO(text)
    games = []
    while True:
        game = chess.pgn.read_game(bio)
        if game is None:
            break
        games.append(game)
    loss_game = next(g for g in games if g.headers.get('Black','').lower()=='groborger')
    board = loss_game.board()
    for idx, node in enumerate(loss_game.mainline(), start=1):
        move = node.move
        if board.turn == chess.BLACK:
            labels = _hanging_user_piece_labels_after_move(board.fen(), move.uci())
            if labels:
                print(idx, board.fullmove_number, move.uci(), board.piece_at(move.from_square), labels)
        board.push(move)

if __name__=='__main__':
    main()
