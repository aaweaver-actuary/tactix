import shutil
from pathlib import Path

import chess

from tactix.config import Settings
from tactix.stockfish_runner import StockfishEngine
from tactix.tactics_analyzer import analyze_position

BASE_FEN = "6k1/4qp2/3p4/8/2B5/5N2/4R3/6K1 w - - 0 1"


def analyze_move(board: chess.Board, move: chess.Move, engine: StockfishEngine, settings: Settings):
    position = {
        "game_id": "loss-game",
        "user": "chesscom",
        "source": "chesscom",
        "fen": board.fen(),
        "ply": board.ply(),
        "move_number": board.fullmove_number,
        "side_to_move": "white" if board.turn == chess.WHITE else "black",
        "uci": move.uci(),
        "san": board.san(move),
        "clock_seconds": None,
        "is_legal": True,
    }
    result = analyze_position(position, engine, settings=settings)
    if not result:
        return None
    tactic_row, outcome_row = result
    return tactic_row, outcome_row


def find_missed_move(
    board: chess.Board, engine: StockfishEngine, settings: Settings, piece_type: int
):
    for move in board.legal_moves:
        mover = board.piece_at(move.from_square)
        if not mover or mover.piece_type != piece_type:
            continue
        result = analyze_move(board, move, engine, settings)
        if not result:
            continue
        tactic_row, outcome_row = result
        if tactic_row["motif"] != "hanging_piece":
            continue
        if outcome_row["result"] != "missed":
            continue
        return move
    return None


if __name__ == "__main__":
    settings = Settings(
        source="chesscom",
        chesscom_user="chesscom",
        chesscom_profile="bullet",
        stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
    )
    settings.apply_chesscom_profile("bullet")
    settings.stockfish_movetime_ms = 60
    settings.stockfish_depth = 8
    settings.stockfish_multipv = 2
    settings.stockfish_random_seed = 1

    board = chess.Board(BASE_FEN)
    with StockfishEngine(settings) as engine:
        move1 = find_missed_move(board, engine, settings, chess.KNIGHT)
        print("move1", move1)
        if move1 is None:
            raise SystemExit(1)
        board.push(move1)
        for black_move in board.legal_moves:
            board_after = board.copy()
            board_after.push(black_move)
            move2 = find_missed_move(board_after, engine, settings, chess.BISHOP)
            if move2 is None:
                continue
            print("found sequence", move1.uci(), black_move.uci(), move2.uci())
            break
        else:
            print("No bishop missed sequence found")
