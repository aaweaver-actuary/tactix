from __future__ import annotations

from pathlib import Path

import chess
import chess.pgn

from tactix.BaseTacticDetector import BaseTacticDetector

USER = "groborger"
FIXTURE_PATH = Path("tests/fixtures/chesscom_2_bullet_games.pgn")


def _capture_square(board: chess.Board, move: chess.Move) -> chess.Square:
    if board.is_en_passant(move):
        return move.to_square + (-8 if board.turn == chess.WHITE else 8)
    return move.to_square


def _hanging_moved_piece(board: chess.Board, move: chess.Move) -> bool:
    if move not in board.legal_moves:
        return False
    moved_piece = board.piece_at(move.from_square)
    if moved_piece is None:
        return False
    mover_color = board.turn
    board.push(move)
    target_square = move.to_square
    if not board.is_attacked_by(not mover_color, target_square):
        return False
    is_unprotected = not board.is_attacked_by(mover_color, target_square)
    is_favorable = False
    for response in board.legal_moves:
        if not board.is_capture(response):
            continue
        capture_square = _capture_square(board, response)
        if capture_square != target_square:
            continue
        mover_piece = board.piece_at(response.from_square)
        if mover_piece is None:
            continue
        is_favorable = BaseTacticDetector.piece_value(
            moved_piece.piece_type
        ) > BaseTacticDetector.piece_value(mover_piece.piece_type)
        if is_favorable:
            break
    return is_unprotected or is_favorable


def _user_color(headers: chess.pgn.Headers, user: str) -> bool:
    white = (headers.get("White") or "").lower()
    black = (headers.get("Black") or "").lower()
    if white == user.lower():
        return chess.WHITE
    if black == user.lower():
        return chess.BLACK
    raise SystemExit("user not in game")


if __name__ == "__main__":
    with FIXTURE_PATH.open() as handle:
        game = chess.pgn.read_game(handle)
    if game is None:
        raise SystemExit("no game")

    board = game.board()
    user_color = _user_color(game.headers, USER)

    print("candidate bishop blunders:")
    for node in game.mainline():
        move = node.move
        if move is None:
            continue
        if board.turn == user_color:
            for candidate in board.legal_moves:
                piece = board.piece_at(candidate.from_square)
                if piece is None or piece.piece_type != chess.BISHOP:
                    continue
                if _hanging_moved_piece(board.copy(), candidate):
                    print(
                        board.fullmove_number,
                        board.fen(),
                        candidate.uci(),
                    )
        board.push(move)
