from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import chess

from tactix._is_moved_piece_hanging_after_move import _is_moved_piece_hanging_after_move
from tactix.config import Settings
from tactix.db.duckdb_store import get_connection
from tactix.pgn_utils import extract_last_timestamp_ms, split_pgn_chunks
from tactix.pipeline import run_daily_game_sync

USER = "groborger"
FIXTURE_PATH = Path("tests/fixtures/chesscom_2_bullet_games.pgn")


def _capture_square(board: chess.Board, move: chess.Move) -> chess.Square:
    if board.is_en_passant(move):
        return move.to_square + (-8 if board.turn == chess.WHITE else 8)
    return move.to_square


def main() -> None:
    if not shutil.which("stockfish"):
        raise SystemExit("stockfish not on PATH")

    work_dir = Path(tempfile.mkdtemp(dir="tmp-logs"))
    db_path = work_dir / "debug_chesscom_2026_02_01.duckdb"
    settings = Settings(
        source="chesscom",
        user=USER,
        chesscom_user=USER,
        duckdb_path=db_path,
        checkpoint_path=work_dir / "chesscom_since.txt",
        metrics_version_file=work_dir / "metrics_chesscom.txt",
        chesscom_fixture_pgn_path=FIXTURE_PATH,
        chesscom_use_fixture_when_no_token=True,
        chesscom_profile="bullet",
        stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
        stockfish_movetime_ms=60,
        stockfish_depth=8,
        stockfish_multipv=2,
    )

    pgn_text = FIXTURE_PATH.read_text()
    timestamps = [extract_last_timestamp_ms(chunk) for chunk in split_pgn_chunks(pgn_text)]
    window_start = min(timestamps) - 1000
    window_end = max(timestamps) + 1000

    run_daily_game_sync(settings, window_start_ms=window_start, window_end_ms=window_end)

    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT t.tactic_id, t.motif, o.result, t.best_uci, p.fen, p.uci
            FROM tactics t
            JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
            JOIN positions p ON p.position_id = t.position_id
            WHERE t.motif = 'hanging_piece'
            ORDER BY t.tactic_id
            """
        ).fetchall()
        print("rows", len(rows))
        for row in rows:
            print(row[:4])
        missed = [r for r in rows if r[2] == "missed"]
        print("missed rows", len(missed))
        for tactic_id, motif, result, best_uci, fen, user_move_uci in missed:
            print("missed", tactic_id, best_uci, user_move_uci, fen)

        labels = set()
        for _, _, result, best_uci, fen, user_move_uci in missed:
            board = chess.Board(fen)
            move = chess.Move.from_uci(user_move_uci)
            if move not in board.legal_moves:
                print("illegal move", user_move_uci, fen)
                continue
            moved_piece = board.piece_at(move.from_square)
            user_color = board.turn
            board.push(move)
            if moved_piece is None:
                continue
            target_square = move.to_square
            if board.is_attacked_by(not user_color, target_square):
                is_unprotected = not board.is_attacked_by(user_color, target_square)
                is_favorable = False
                for response in board.legal_moves:
                    if not board.is_capture(response):
                        continue
                    if _capture_square(board, response) != target_square:
                        continue
                    mover_piece = board.piece_at(response.from_square)
                    if mover_piece is None:
                        continue
                    is_favorable = moved_piece.piece_type > mover_piece.piece_type
                    if is_favorable:
                        break
                if is_unprotected or is_favorable:
                    if moved_piece.piece_type == chess.KNIGHT:
                        labels.add("knight")
                    elif moved_piece.piece_type == chess.BISHOP:
                        labels.add("bishop")
        print("labels", labels)

        focus_moves = ["e5e4", "d7e5", "h8f8", "c6e5", "f8c5", "c5e7"]
        for move in focus_moves:
            focus_rows = conn.execute(
                """
                SELECT t.tactic_id, t.motif, o.result, t.best_uci, t.eval_cp, o.eval_delta,
                       p.fen, p.uci
                FROM tactics t
                JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
                JOIN positions p ON p.position_id = t.position_id
                WHERE p.uci = ?
                ORDER BY t.tactic_id
                """,
                [move],
            ).fetchall()
            extra = []
            for row in focus_rows:
                _tactic_id, _motif, _result, _best_uci, _eval_cp, _eval_delta, fen, uci = row
                board_before = chess.Board(fen)
                move_obj = chess.Move.from_uci(str(uci))
                if move_obj not in board_before.legal_moves:
                    extra.append((uci, "illegal"))
                    continue
                board_after = board_before.copy()
                board_after.push(move_obj)
                hanging = _is_moved_piece_hanging_after_move(
                    board_before, board_after, move_obj, board_before.turn
                )
                extra.append((uci, hanging))
            print("focus", move, focus_rows, extra)
    finally:
        conn.close()

    print("db", db_path)


if __name__ == "__main__":
    main()
