import shutil
import tempfile
from pathlib import Path
import unittest

from tactix.config import Settings
from tactix.lichess_client import read_checkpoint
from tactix.pipeline import run_daily_game_sync


class PipelineStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "lichess_rapid_sample.pgn"
        )

    def test_checkpoint_and_metrics_files_written(self) -> None:
        settings = Settings(
            duckdb_path=self.tmp_dir / "tactix.duckdb",
            checkpoint_path=self.tmp_dir / "since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            fixture_pgn_path=self.fixture_path,
            use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
        )

        result = run_daily_game_sync(settings)

        self.assertGreater(result["metrics_version"], 0)
        self.assertTrue(settings.metrics_version_file.exists())
        self.assertEqual(
            int(settings.metrics_version_file.read_text().strip()),
            result["metrics_version"],
        )

        ckpt_value = read_checkpoint(settings.checkpoint_path)
        self.assertGreater(ckpt_value, 0)
        self.assertEqual(ckpt_value, int(settings.checkpoint_path.read_text().strip()))


if __name__ == "__main__":
    unittest.main()
