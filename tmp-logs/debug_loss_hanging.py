import sys
from pathlib import Path

import chess

sys.path.append(str(Path(__file__).resolve().parents[1]))

from tactix.db.duckdb_store import get_connection
from tests import test_chesscom_bullet_pipeline_2026_02_01 as mod


path = mod._run_fixture_pipeline()
conn = get_connection(path)
print(conn.execute("pragma table_info('games')").fetchall())
print(conn.execute("SELECT * FROM games LIMIT 5").fetchall())
loss_game_id = conn.execute(
    """
    SELECT game_id
    FROM games
    WHERE source = 'chesscom'
    ORDER BY game_id
    LIMIT 1
    """
).fetchone()[0]
rows = conn.execute(
    """
    SELECT t.tactic_id, t.best_uci, t.motif, o.result, p.fen, p.uci, p.move_number
    FROM tactics t
    JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
    JOIN positions p ON p.position_id = t.position_id
    WHERE t.game_id = ?
    AND t.motif = 'hanging_piece'
    AND o.result = 'missed'
    ORDER BY p.move_number
    """,
    [loss_game_id],
).fetchall()
print("rows", len(rows))
for tactic_id, best_uci, motif, result, fen, user_move_uci, move_number in rows:
    board = chess.Board(fen)
    move = chess.Move.from_uci(user_move_uci) if user_move_uci else None
    moved_piece = board.piece_at(move.from_square) if move else None
    moved_label = None
    if moved_piece and moved_piece.piece_type == chess.KNIGHT:
        moved_label = "knight"
    elif moved_piece and moved_piece.piece_type == chess.BISHOP:
        moved_label = "bishop"
    print(move_number, user_move_uci, moved_label, best_uci, fen)
conn.close()
print("db", path)
