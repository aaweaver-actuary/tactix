import shutil
from pathlib import Path

from tactix.config import Settings
from tactix.StockfishEngine import StockfishEngine
from tests.test_chesscom_bullet_pipeline_2026_02_01 import (
    _build_loss_game,
    _build_win_game,
    _serialize_games,
)


def main() -> None:
    settings = Settings(
        source="chesscom",
        chesscom_user="chesscom",
        chesscom_profile="bullet",
        stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
        stockfish_movetime_ms=60,
        stockfish_depth=8,
        stockfish_multipv=2,
        stockfish_random_seed=1,
    )
    settings.apply_chesscom_profile("bullet")

    with StockfishEngine(settings) as engine:
        loss_game = _build_loss_game(
            engine,
            settings,
            utc_date="2026.02.01",
            utc_time="12:00:00",
            game_id="2026020101",
            white_elo=1500,
            black_elo=1620,
        )
    win_game = _build_win_game(
        utc_date="2026.02.01",
        utc_time="13:00:00",
        game_id="2026020102",
        white_elo=1480,
        black_elo=1500,
    )
    games = [loss_game, win_game]
    print("games", len(games), [g.headers.get("Site") for g in games])
    print("loss_game.next()", loss_game.next())
    print("loss_game.board().fen()", loss_game.board().fen())
    loss_text = _serialize_games([loss_game])
    win_text = _serialize_games([win_game])
    print("loss_text events", loss_text.count("[Event"))
    print("win_text events", win_text.count("[Event"))
    from tactix.extract_positions__pgn import extract_positions

    print("loss positions", len(extract_positions(loss_text, "chesscom", "chesscom")))
    print("win positions", len(extract_positions(win_text, "chesscom", "chesscom")))
    print(_serialize_games(games))


if __name__ == "__main__":
    main()
