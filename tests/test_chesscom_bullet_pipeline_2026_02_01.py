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


BASE_SETTINGS__CHESSCOM_BULLET = {
    "source": "chesscom",
    "chesscom_user": "chesscom",
    "chesscom_profile": "bullet",
    "chesscom_use_fixture_when_no_token": True,
    "stockfish_movetime_ms": 60,
    "stockfish_depth": 10,
    "stockfish_multipv": 1,
}


class ChesscomBulletPipelineFeb012026Tests(unittest.TestCase):
    @staticmethod
    def _fixture_path() -> Path:
        return (
            Path(__file__).resolve().parent / "fixtures" / "chesscom_bullet_2026_02_01.pgn"
        )

    @staticmethod
    def _build_settings(tmp_dir: Path, fixture_path: Path) -> Settings:
        settings = Settings(
            **BASE_SETTINGS__CHESSCOM_BULLET,
            duckdb_path=tmp_dir / "tactix_chesscom.duckdb",
            chesscom_checkpoint_path=tmp_dir / "chesscom_since_bullet.txt",
            metrics_version_file=tmp_dir / "metrics_chesscom.txt",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
        )
        settings.apply_chesscom_profile("bullet")
        settings.chesscom_fixture_pgn_path = fixture_path
        return settings

    @staticmethod
    def _build_window_ms() -> tuple[int, int]:
        start = int(datetime(2026, 2, 1, tzinfo=UTC).timestamp() * 1000)
        end = int(datetime(2026, 2, 2, tzinfo=UTC).timestamp() * 1000)
        return start, end

    @staticmethod
    def _load_raw_rows(conn: object) -> list[tuple[str, str, str]]:
        return conn.execute(
            "SELECT game_id, pgn, time_control FROM raw_pgns WHERE source='chesscom' ORDER BY game_id"
        ).fetchall()

    @staticmethod
    def _load_missed_rows(conn: object, loss_game_id: str) -> list[tuple[str, str, str, str]]:
        return conn.execute(
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

    def _read_game(self, pgn: str) -> chess.pgn.Game:
        game = chess.pgn.read_game(StringIO(pgn))
        assert game is not None
        return game

    @staticmethod
    def _read_headers(game: chess.pgn.Game) -> tuple[str, str, str, int, int]:
        headers = game.headers
        return (
            headers.get("Result"),
            headers.get("White"),
            headers.get("Black"),
            int(headers.get("WhiteElo", "0")),
            int(headers.get("BlackElo", "0")),
        )

    def _resolve_outcome(self, game: chess.pgn.Game, user: str) -> tuple[str, int, bool]:
        result, white, black, white_elo, black_elo = self._read_headers(game)
        self.assertIn(user, (white, black))
        is_user_white = white == user
        user_rating = white_elo if is_user_white else black_elo
        opponent_rating = black_elo if is_user_white else white_elo
        win = result == ("1-0" if is_user_white else "0-1")
        return ("win" if win else "loss", opponent_rating - user_rating, win)

    def _build_game_summaries(
        self,
        raw_rows: list[tuple[str, str, str]],
        user: str,
    ) -> list[tuple[str, str, int, bool]]:
        summaries = []
        for game_id, pgn, _time_control in raw_rows:
            game = self._read_game(pgn)
            outcome, diff, win = self._resolve_outcome(game, user)
            summaries.append((str(game_id), outcome, diff, win))
        return summaries

    def _assert_rating_diffs(self, rating_diffs: dict[str, int], loss_game_id: str) -> None:
        for game_id, diff in rating_diffs.items():
            if game_id == loss_game_id:
                self.assertGreater(diff, 50)
            else:
                self.assertLessEqual(diff, 50)

    def _assert_missed_row(self, best_uci: str, result: str, user_uci: str) -> None:
        self.assertEqual(result, "missed")
        self.assertNotEqual(best_uci, user_uci)

    def _capture_type_for_move(self, fen: str, best_uci: str) -> int:
        board = chess.Board(str(fen))
        move = chess.Move.from_uci(best_uci)
        captured = board.piece_at(move.to_square)
        self.assertIsNotNone(captured)
        return captured.piece_type if captured else chess.PAWN

    def _collect_missed_details(
        self,
        missed_rows: list[tuple[str, str, str, str]],
    ) -> tuple[set[int], set[str]]:
        captured_types: set[int] = set()
        user_moves: set[str] = set()
        for best_uci, result, fen, user_uci in missed_rows:
            self._assert_missed_row(best_uci, result, user_uci)
            captured_types.add(self._capture_type_for_move(fen, best_uci))
            user_moves.add(str(user_uci))
        return captured_types, user_moves

    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_pipeline_validates_bullet_games_for_2026_02_01(self) -> None:
        tmp_dir = Path(tempfile.mkdtemp())
        fixture_path = self._fixture_path()
        settings = self._build_settings(tmp_dir, fixture_path)
        window_start_ms, window_end_ms = self._build_window_ms()

        run_daily_game_sync(
            settings,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
        )

        conn = get_connection(settings.duckdb_path)
        raw_rows = self._load_raw_rows(conn)
        self.assertEqual(len(raw_rows), 2)
        self.assertTrue(all(row[2] == "60" for row in raw_rows))
        summaries = self._build_game_summaries(raw_rows, settings.chesscom_user)
        outcomes = [summary[1] for summary in summaries]
        rating_diffs = {game_id: diff for game_id, _outcome, diff, _win in summaries}
        loss_game_ids = [game_id for game_id, _outcome, _diff, win in summaries if not win]

        self.assertEqual(outcomes.count("win"), 1)
        self.assertEqual(outcomes.count("loss"), 1)
        self.assertEqual(len(loss_game_ids), 1)
        loss_game_id = loss_game_ids[0]

        self._assert_rating_diffs(rating_diffs, loss_game_id)
        missed_rows = self._load_missed_rows(conn, loss_game_id)

        self.assertEqual(len(missed_rows), 2)

        captured_types, user_moves = self._collect_missed_details(missed_rows)

        self.assertEqual(captured_types, {chess.KNIGHT, chess.BISHOP})
        self.assertEqual(user_moves, {"g8h7", "d8h8"})


if __name__ == "__main__":
    unittest.main()
