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


def _hanging_moved_piece(board: chess.Board, move: chess.Move) -> str | None:
    if move not in board.legal_moves:
        return None
    moved_piece = board.piece_at(move.from_square)
    if moved_piece is None:
        return None
    user_color = board.turn
    board.push(move)
    target_square = move.to_square
    if not board.is_attacked_by(not user_color, target_square):
        return None
    is_unprotected = not board.is_attacked_by(user_color, target_square)
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


def _user_color(headers: chess.pgn.Headers, user: str) -> bool:
    white = (headers.get("White") or "").lower()
    black = (headers.get("Black") or "").lower()
    if white == user.lower():
        return chess.WHITE
    if black == user.lower():
        return chess.BLACK
    raise SystemExit("user not in game")


def main() -> None:
    text = FIXTURE_PATH.read_text()
    games = []
    while text:
        game = chess.pgn.read_game(iter(text.splitlines()))
        if game is None:
            break
        games.append(game)
        break


if __name__ == "__main__":
    # load games via PGN parser
    with FIXTURE_PATH.open() as handle:
        games = []
        while True:
            game = chess.pgn.read_game(handle)
            if game is None:
                break
            games.append(game)

    loss_game = None
    win_game = None
    for game in games:
        headers = game.headers
        result = headers.get("Result")
        color = _user_color(headers, USER)
        if result == "1-0" and color == chess.BLACK:
            loss_game = game
            break
        if result == "1-0" and color == chess.WHITE:
            win_game = game
    if loss_game is None:
        raise SystemExit("loss game not found")

    if win_game is None:
        raise SystemExit("win game not found")

    def inspect_game(label: str, game: chess.pgn.Game) -> None:
        board = game.board()
        user_color = _user_color(game.headers, USER)
        moves = []
        inspected = []
        for node in game.mainline():
            move = node.move
            if move is None:
                continue
            if board.turn == user_color:
                tmp_board = board.copy()
                moved_piece = tmp_board.piece_at(move.from_square)
                label_move = _hanging_moved_piece(tmp_board, move)
                if moved_piece and moved_piece.piece_type in {chess.KNIGHT, chess.BISHOP}:
                    after_board = board.copy()
                    after_board.push(move)
                    target = move.to_square
                    attackers = list(after_board.attackers(not user_color, target))
                    defenders = list(after_board.attackers(user_color, target))
                    favorable = []
                    for response in after_board.legal_moves:
                        if not after_board.is_capture(response):
                            continue
                        capture_square = _capture_square(after_board, response)
                        if capture_square != target:
                            continue
                        responder_piece = after_board.piece_at(response.from_square)
                        if responder_piece is None:
                            continue
                        if BaseTacticDetector.piece_value(moved_piece.piece_type) > BaseTacticDetector.piece_value(
                            responder_piece.piece_type
                        ):
                            favorable.append(response.uci())
                    inspected.append((
                        board.fullmove_number,
                        move.uci(),
                        moved_piece.piece_type,
                        label_move,
                        attackers,
                        defenders,
                        favorable,
                        board.fen(),
                    ))
                if label_move:
                    moves.append((board.fullmove_number, move.uci(), label_move, board.fen()))
            board.push(move)

        print(f"hanging moved piece moves ({label}):")
        for move_info in moves:
            print(move_info)
        print(f"knight/bishop moves inspected ({label}):")
        for info in inspected:
            print(info)

    inspect_game("loss", loss_game)
    inspect_game("win", win_game)
