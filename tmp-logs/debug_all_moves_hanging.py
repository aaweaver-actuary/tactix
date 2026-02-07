from __future__ import annotations

from pathlib import Path

import chess
import chess.pgn

from tactix.BaseTacticDetector import BaseTacticDetector

FIXTURE_PATH = Path("tests/fixtures/chesscom_2_bullet_games.pgn")


def _capture_square(board: chess.Board, move: chess.Move) -> chess.Square:
    if board.is_en_passant(move):
        return move.to_square + (-8 if board.turn == chess.WHITE else 8)
    return move.to_square


def _hanging_moved_piece(board: chess.Board, move: chess.Move) -> str | None:
    if move not in board.legal_moves:
        return None
    moved_piece = board.piece_at(move.from_square)
    if moved_piece is None:
        return None
    mover_color = board.turn
    board.push(move)
    target_square = move.to_square
    if not board.is_attacked_by(not mover_color, target_square):
        return None
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
    if not (is_unprotected or is_favorable):
        return None
    if moved_piece.piece_type == chess.KNIGHT:
        return "knight"
    if moved_piece.piece_type == chess.BISHOP:
        return "bishop"
    return None


if __name__ == "__main__":
    games = []
    with FIXTURE_PATH.open() as handle:
        while True:
            game = chess.pgn.read_game(handle)
            if game is None:
                break
            games.append(game)

    for idx, game in enumerate(games, start=1):
        board = game.board()
        hits = []
        for node in game.mainline():
            move = node.move
            if move is None:
                continue
            label = _hanging_moved_piece(board.copy(), move)
            if label:
                hits.append((board.fullmove_number, board.turn, move.uci(), label, board.fen()))
            board.push(move)

        print(f"all hanging moved-piece moves (game {idx}):")
        for hit in hits:
            print(hit)
