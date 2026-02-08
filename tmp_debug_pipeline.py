import tempfile
from pathlib import Path

import chess

from tests.test_api_chesscom_bullet_pipeline_canonical import (
    _hanging_user_piece_labels_after_move,
    _load_games,
    _loss_game_id,
    _run_pipeline,
)
from tactix.db.duckdb_store import get_connection

def main():
    out_path = Path('tmp_debug_pipeline.txt')
    base_dir = Path(tempfile.mkdtemp())
    db_path = _run_pipeline(base_dir)
    out_path.write_text('')
    with out_path.open('a') as f:
        f.write(f'db: {db_path}\n')
        conn = get_connection(db_path)
        try:
            games = _load_games(conn)
            loss_game_id = _loss_game_id(games)
            rows = conn.execute(
                "SELECT t.tactic_id, t.position_id, t.best_uci, p.fen, p.uci, o.result, t.motif FROM tactics t JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id JOIN positions p ON p.position_id = t.position_id WHERE t.game_id = ? AND t.motif = 'hanging_piece'",
                [loss_game_id],
            ).fetchall()
            f.write(f'count: {len(rows)}\n')
            for row in rows:
                tactic_id, position_id, best_uci, fen, user_move_uci, outcome, motif = row
                board = chess.Board(fen)
                move = chess.Move.from_uci(user_move_uci)
                piece = board.piece_at(move.from_square)
                piece_symbol = piece.symbol() if piece else None
                labels = _hanging_user_piece_labels_after_move(fen, user_move_uci)
                f.write(
                    f'{tactic_id} {position_id} {best_uci} {user_move_uci} {outcome} piece={piece_symbol} labels={labels}\n'
                )
        finally:
            conn.close()
    print('done, wrote', out_path)

if __name__ == '__main__':
    main()
