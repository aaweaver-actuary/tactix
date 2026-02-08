import chess
from tactix.db.duckdb_store import get_connection


def main():
    conn = get_connection('/Users/andy/tactix/tmpxyyemft3/tactix_feature_pipeline_validation_2026_02_01.duckdb')
    row = conn.execute(
        "SELECT p.fen, p.uci FROM positions p JOIN tactics t ON t.position_id = p.position_id WHERE t.tactic_id = 14"
    ).fetchone()
    out_path = 'tmp_debug_bishop_out.txt'
    with open(out_path, 'w') as handle:
        handle.write(f'row: {row}\n')
        fen, uci = row
        board = chess.Board(fen)
        move = chess.Move.from_uci(uci)
        handle.write(f'move: {move.uci()} piece: {board.piece_at(move.from_square)}\n')
        board.push(move)
        handle.write(
            f'attacked_by_white: {board.is_attacked_by(chess.WHITE, move.to_square)} attacked_by_black: {board.is_attacked_by(chess.BLACK, move.to_square)}\n'
        )
        handle.write(f'unprotected (from mover): {not board.is_attacked_by(board.turn, move.to_square)}\n')
        handle.write('legal capture responses:\n')
        for resp in board.legal_moves:
            if not board.is_capture(resp):
                continue
            capture_square = resp.to_square if not board.is_en_passant(resp) else resp.to_square + (
                -8 if board.turn == chess.WHITE else 8
            )
            if capture_square != move.to_square:
                continue
            handle.write(f'  {resp.uci()} piece {board.piece_at(resp.from_square)}\n')
    conn.close()
    print('wrote', out_path)

if __name__ == '__main__':
    main()
