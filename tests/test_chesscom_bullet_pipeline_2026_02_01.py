import shutil
import tempfile
import unittest
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import chess
import chess.pgn

from tactix.config import Settings
from tactix.db.duckdb_store import get_connection
from tactix.pipeline import run_daily_game_sync


class ChesscomBulletPipelineFeb012026Tests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_pipeline_validates_bullet_games_for_2026_02_01(self) -> None:
        tmp_dir = Path(tempfile.mkdtemp())
        fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "chesscom_bullet_2026_02_01.pgn"
        )
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="bullet",
            duckdb_path=tmp_dir / "tactix_chesscom.duckdb",
            chesscom_checkpoint_path=tmp_dir / "chesscom_since_bullet.txt",
            metrics_version_file=tmp_dir / "metrics_chesscom.txt",
            chesscom_use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=10,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("bullet")
        settings.chesscom_fixture_pgn_path = fixture_path

        window_start_ms = int(datetime(2026, 2, 1, tzinfo=UTC).timestamp() * 1000)
        window_end_ms = int(datetime(2026, 2, 2, tzinfo=UTC).timestamp() * 1000)

        run_daily_game_sync(
            settings,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
        )

        conn = get_connection(settings.duckdb_path)
        raw_rows = conn.execute(
            "SELECT game_id, pgn, time_control FROM raw_pgns WHERE source='chesscom' ORDER BY game_id"
        ).fetchall()
        self.assertEqual(len(raw_rows), 2)
        self.assertTrue(all(row[2] == "60" for row in raw_rows))

        outcomes: list[str] = []
        rating_diffs: dict[str, int] = {}
        loss_game_id: str | None = None

        for game_id, pgn, _time_control in raw_rows:
            game = chess.pgn.read_game(StringIO(pgn))
            self.assertIsNotNone(game)
            headers = game.headers
            result = headers.get("Result")
            white = headers.get("White")
            black = headers.get("Black")
            white_elo = int(headers.get("WhiteElo", "0"))
            black_elo = int(headers.get("BlackElo", "0"))
            self.assertIn(settings.chesscom_user, (white, black))
            if white == settings.chesscom_user:
                user_rating = white_elo
                opponent_rating = black_elo
                win = result == "1-0"
            else:
                user_rating = black_elo
                opponent_rating = white_elo
                win = result == "0-1"
            outcomes.append("win" if win else "loss")
            rating_diffs[str(game_id)] = opponent_rating - user_rating
            if not win:
                loss_game_id = str(game_id)

        self.assertEqual(outcomes.count("win"), 1)
        self.assertEqual(outcomes.count("loss"), 1)
        self.assertIsNotNone(loss_game_id)
        loss_game_id = loss_game_id or ""

        for game_id, diff in rating_diffs.items():
            if game_id == loss_game_id:
                self.assertGreater(diff, 50)
            else:
                self.assertLessEqual(diff, 50)

        missed_rows = conn.execute(
            """
            SELECT t.best_uci, o.result, p.fen, p.uci
            FROM tactics t
            JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
            JOIN positions p ON p.position_id = t.position_id
            WHERE t.game_id = ? AND t.motif = 'hanging_piece' AND o.result = 'missed'
            ORDER BY t.tactic_id
            """,
            [loss_game_id],
        ).fetchall()

        self.assertEqual(len(missed_rows), 2)

        captured_types: set[int] = set()
        user_moves: set[str] = set()
        for best_uci, result, fen, user_uci in missed_rows:
            self.assertEqual(result, "missed")
            self.assertNotEqual(best_uci, user_uci)
            board = chess.Board(str(fen))
            move = chess.Move.from_uci(best_uci)
            captured = board.piece_at(move.to_square)
            self.assertIsNotNone(captured)
            captured_types.add(captured.piece_type)
            user_moves.add(str(user_uci))

        self.assertEqual(captured_types, {chess.KNIGHT, chess.BISHOP})
        self.assertEqual(user_moves, {"g8h7", "d8h8"})


if __name__ == "__main__":
    unittest.main()
