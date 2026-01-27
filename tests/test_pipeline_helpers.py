import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from tactix.config import Settings
import tactix.pipeline as pipeline


class PipelineHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.settings = Settings(
            user="alice",
            source="lichess",
            duckdb_path=self.tmp_dir / "tactix.duckdb",
            checkpoint_path=self.tmp_dir / "since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            fixture_pgn_path=self.tmp_dir / "fixtures.pgn",
            use_fixture_when_no_token=True,
        )

    def test_coerce_helpers_and_normalize_game_row(self) -> None:
        row = {
            "game_id": 101,
            "pgn": b"1. e4 *",
            "last_timestamp_ms": "42",
            "fetched_at": "not-a-date",
        }

        normalized = pipeline._normalize_game_row(row, self.settings)

        self.assertEqual(normalized["game_id"], "101")
        self.assertEqual(normalized["user"], "alice")
        self.assertEqual(normalized["source"], "lichess")
        self.assertEqual(normalized["pgn"], "1. e4 *")
        self.assertEqual(normalized["last_timestamp_ms"], 42)
        self.assertIsInstance(normalized["fetched_at"], datetime)

        self.assertEqual(pipeline._coerce_int(True), 1)
        self.assertEqual(pipeline._coerce_int("7"), 7)
        self.assertEqual(pipeline._coerce_int(3.9), 3)
        self.assertEqual(pipeline._coerce_int("bad"), 0)
        self.assertEqual(pipeline._coerce_str(None), "")

    def test_filtering_and_dedupe_helpers(self) -> None:
        rows = [
            {
                "game_id": "g1",
                "source": "lichess",
                "last_timestamp_ms": 10,
                "pgn": "p1",
            },
            {
                "game_id": "g1",
                "source": "lichess",
                "last_timestamp_ms": 10,
                "pgn": "p1",
            },
            {
                "game_id": "g1",
                "source": "lichess",
                "last_timestamp_ms": 11,
                "pgn": "p1b",
            },
            {
                "game_id": "g2",
                "source": "lichess",
                "last_timestamp_ms": 20,
                "pgn": "p2",
            },
            {
                "game_id": "g3",
                "source": "lichess",
                "last_timestamp_ms": 30,
                "pgn": "p3",
            },
        ]

        deduped = pipeline._dedupe_games(rows)
        self.assertEqual(len(deduped), 4)

        filtered = pipeline._filter_games_by_window(deduped, start_ms=15, end_ms=25)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["game_id"], "g2")
        self.assertTrue(all(row["last_timestamp_ms"] < 25 for row in filtered))

    def test_resolve_side_to_move_filter(self) -> None:
        self.settings.source = "lichess"
        self.settings.lichess_profile = "rapid"
        self.assertEqual(pipeline._resolve_side_to_move_filter(self.settings), "black")

        self.settings.source = "chesscom"
        self.settings.chesscom_profile = "daily"
        self.assertEqual(pipeline._resolve_side_to_move_filter(self.settings), "black")

        self.settings.chesscom_profile = "unknown"
        self.assertIsNone(pipeline._resolve_side_to_move_filter(self.settings))

    def test_expand_pgn_rows_splits_multi_game_pgn(self) -> None:
        pgn_one = """[Event \"Test 1\"]
[Site \"https://lichess.org/AbcDef12\"]
[UTCDate \"2020.01.02\"]
[UTCTime \"03:04:05\"]
[White \"alice\"]
[Black \"bob\"]
[WhiteElo \"1200\"]
[BlackElo \"1300\"]
[TimeControl \"300+0\"]
[Result \"*\"]

1. e4 *
"""
        pgn_two = """[Event \"Test 2\"]
[Site \"https://lichess.org/ZyXwVu98\"]
[UTCDate \"2020.01.03\"]
[UTCTime \"04:05:06\"]
[White \"alice\"]
[Black \"carol\"]
[WhiteElo \"1250\"]
[BlackElo \"1350\"]
[TimeControl \"600+0\"]
[Result \"*\"]

1. d4 *
"""
        combined = f"{pgn_one}\n\n{pgn_two}"
        rows = [
            pipeline._normalize_game_row(
                {
                    "game_id": "bulk",
                    "user": "alice",
                    "source": "lichess",
                    "pgn": combined,
                    "last_timestamp_ms": 0,
                },
                self.settings,
            )
        ]

        expanded = pipeline._expand_pgn_rows(rows, self.settings)

        self.assertEqual(len(expanded), 2)
        self.assertEqual(expanded[0]["game_id"], "AbcDef12")
        self.assertEqual(expanded[1]["game_id"], "ZyXwVu98")
        self.assertGreater(expanded[0]["last_timestamp_ms"], 0)
        self.assertGreater(expanded[1]["last_timestamp_ms"], 0)
        self.assertNotEqual(
            expanded[0]["last_timestamp_ms"], expanded[1]["last_timestamp_ms"]
        )

    def test_analysis_checkpoint_helpers(self) -> None:
        checkpoint_path = self.tmp_dir / "analysis.json"
        signature = pipeline._analysis_signature(["g1", "g2"], 3, "lichess")

        self.assertEqual(
            pipeline._read_analysis_checkpoint(checkpoint_path, signature), -1
        )

        pipeline._write_analysis_checkpoint(checkpoint_path, signature, 2)
        self.assertEqual(
            pipeline._read_analysis_checkpoint(checkpoint_path, signature), 2
        )

        checkpoint_path.write_text("not-json")
        self.assertEqual(
            pipeline._read_analysis_checkpoint(checkpoint_path, signature), -1
        )

        pipeline._write_analysis_checkpoint(checkpoint_path, "other", 1)
        self.assertEqual(
            pipeline._read_analysis_checkpoint(checkpoint_path, signature), -1
        )

        pipeline._clear_analysis_checkpoint(checkpoint_path)
        self.assertFalse(checkpoint_path.exists())

    def test_filter_backfill_games_skips_cached(self) -> None:
        rows = [
            {
                "game_id": "g1",
                "source": "lichess",
                "last_timestamp_ms": 10,
                "pgn": "pgn-1",
            },
            {
                "game_id": "g2",
                "source": "lichess",
                "last_timestamp_ms": 20,
                "pgn": "pgn-2",
            },
        ]
        existing_hash = pipeline.hash_pgn("pgn-1")

        with (
            patch(
                "tactix.pipeline.fetch_latest_pgn_hashes",
                return_value={"g1": existing_hash},
            ),
            patch(
                "tactix.pipeline.fetch_position_counts",
                return_value={"g1": 2, "g2": 0},
            ),
        ):
            to_process, skipped = pipeline._filter_backfill_games(
                MagicMock(), rows, "lichess"
            )

        self.assertEqual([row["game_id"] for row in skipped], ["g1"])
        self.assertEqual([row["game_id"] for row in to_process], ["g2"])

        empty_process, empty_skipped = pipeline._filter_backfill_games(
            MagicMock(), [], "lichess"
        )
        self.assertEqual(empty_process, [])
        self.assertEqual(empty_skipped, [])

    def test_validate_raw_pgn_hashes_counts_by_source(self) -> None:
        lichess_rows = [
            {"game_id": "l1", "pgn": "pgn-1"},
            {"game_id": "l2", "pgn": "pgn-2"},
        ]
        chesscom_rows = [
            {"game_id": "c1", "pgn": "pgn-3"},
        ]

        with patch("tactix.pipeline.fetch_latest_pgn_hashes") as fetch_mock:
            fetch_mock.side_effect = [
                {
                    "l1": pipeline.hash_pgn("pgn-1"),
                    "l2": pipeline.hash_pgn("pgn-2"),
                },
                {"c1": pipeline.hash_pgn("pgn-3")},
            ]
            lichess_result = pipeline._validate_raw_pgn_hashes(
                MagicMock(), lichess_rows, "lichess"
            )
            chesscom_result = pipeline._validate_raw_pgn_hashes(
                MagicMock(), chesscom_rows, "chesscom"
            )

        self.assertEqual(lichess_result, {"computed": 2, "matched": 2})
        self.assertEqual(chesscom_result, {"computed": 1, "matched": 1})

        with patch(
            "tactix.pipeline.fetch_latest_pgn_hashes",
            return_value={"l1": "bad-hash"},
        ):
            with self.assertRaises(ValueError):
                pipeline._validate_raw_pgn_hashes(
                    MagicMock(), [{"game_id": "l1", "pgn": "pgn-1"}], "lichess"
                )

    def test_run_migrations_emits_progress(self) -> None:
        progress_events: list[str] = []

        def _progress(payload: dict[str, object]) -> None:
            progress_events.append(str(payload.get("step")))

        result = pipeline.run_migrations(settings=self.settings, progress=_progress)

        self.assertEqual(result["source"], "lichess")
        self.assertIn("migrations_start", progress_events)
        self.assertIn("migrations_complete", progress_events)

    def test_convert_raw_pgns_to_positions_empty(self) -> None:
        result = pipeline.convert_raw_pgns_to_positions(settings=self.settings)
        self.assertEqual(result["games"], 0)
        self.assertEqual(result["positions"], 0)

    def test_analyse_with_retries_restarts_engine(self) -> None:
        class DummyEngine:
            def __init__(self) -> None:
                self.restarts = 0

            def restart(self) -> None:
                self.restarts += 1

        settings = Settings(
            user="alice",
            source="lichess",
            duckdb_path=self.tmp_dir / "analysis.duckdb",
            checkpoint_path=self.tmp_dir / "since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            fixture_pgn_path=self.tmp_dir / "fixtures.pgn",
            use_fixture_when_no_token=True,
            stockfish_max_retries=1,
            stockfish_retry_backoff_ms=10,
        )
        engine = DummyEngine()

        result_value = ({"game_id": "g1"}, {"result": "found"})
        with (
            patch(
                "tactix.pipeline.analyze_position",
                side_effect=[pipeline.chess.engine.EngineError("boom"), result_value],
            ),
            patch("tactix.pipeline.time.sleep", return_value=None) as sleep_mock,
        ):
            result = pipeline._analyse_with_retries(engine, {"fen": ""}, settings)

        self.assertEqual(result, result_value)
        self.assertEqual(engine.restarts, 1)
        sleep_mock.assert_called()


if __name__ == "__main__":
    unittest.main()
