import os
import unittest
from unittest.mock import patch

from tactix import config


class ConfigEnvTests(unittest.TestCase):
    def test_get_settings_uses_lichess_username_from_env(self) -> None:
        with patch.dict(os.environ, {"LICHESS_USERNAME": "envuser"}, clear=True):
            with patch("tactix.config.load_dotenv") as load_dotenv:
                settings = config.get_settings(source="lichess")

        load_dotenv.assert_called_once()
        self.assertEqual(settings.user, "envuser")
        self.assertEqual(settings.lichess_user, "envuser")

    def test_get_settings_applies_lichess_profile_paths(self) -> None:
        settings = config.get_settings(source="lichess", profile="bullet")

        self.assertTrue(
            settings.checkpoint_path.name.endswith("lichess_since_bullet.txt")
        )
        self.assertTrue(
            settings.analysis_checkpoint_path.name.endswith(
                "analysis_checkpoint_lichess_bullet.json"
            )
        )
        self.assertTrue(
            settings.fixture_pgn_path.name.endswith("lichess_bullet_sample.pgn")
        )

    def test_get_settings_applies_lichess_rapid_profile_paths(self) -> None:
        settings = config.get_settings(source="lichess", profile="rapid")

        self.assertTrue(
            settings.checkpoint_path.name.endswith("lichess_since_rapid.txt")
        )
        self.assertTrue(
            settings.analysis_checkpoint_path.name.endswith(
                "analysis_checkpoint_lichess_rapid.json"
            )
        )
        self.assertTrue(
            settings.fixture_pgn_path.name.endswith("lichess_rapid_sample.pgn")
        )

    def test_get_settings_applies_lichess_blitz_profile_paths(self) -> None:
        settings = config.get_settings(source="lichess", profile="blitz")

        self.assertTrue(
            settings.checkpoint_path.name.endswith("lichess_since_blitz.txt")
        )
        self.assertTrue(
            settings.analysis_checkpoint_path.name.endswith(
                "analysis_checkpoint_lichess_blitz.json"
            )
        )
        self.assertTrue(
            settings.fixture_pgn_path.name.endswith("lichess_blitz_sample.pgn")
        )

    def test_get_settings_applies_lichess_classical_profile_paths(self) -> None:
        settings = config.get_settings(source="lichess", profile="classical")

        self.assertTrue(
            settings.checkpoint_path.name.endswith("lichess_since_classical.txt")
        )
        self.assertTrue(
            settings.analysis_checkpoint_path.name.endswith(
                "analysis_checkpoint_lichess_classical.json"
            )
        )
        self.assertTrue(
            settings.fixture_pgn_path.name.endswith("lichess_classical_sample.pgn")
        )

    def test_get_settings_applies_lichess_correspondence_profile_paths(self) -> None:
        settings = config.get_settings(source="lichess", profile="correspondence")

        self.assertTrue(
            settings.checkpoint_path.name.endswith("lichess_since_correspondence.txt")
        )
        self.assertTrue(
            settings.analysis_checkpoint_path.name.endswith(
                "analysis_checkpoint_lichess_correspondence.json"
            )
        )
        self.assertTrue(
            settings.fixture_pgn_path.name.endswith("lichess_correspondence_sample.pgn")
        )

    def test_get_settings_applies_chesscom_bullet_profile_paths(self) -> None:
        settings = config.get_settings(source="chesscom", profile="bullet")

        self.assertTrue(
            settings.checkpoint_path.name.endswith("chesscom_since_bullet.txt")
        )
        self.assertTrue(
            settings.analysis_checkpoint_path.name.endswith(
                "analysis_checkpoint_chesscom_bullet.json"
            )
        )
        self.assertTrue(
            settings.fixture_pgn_path.name.endswith("chesscom_bullet_sample.pgn")
        )
        self.assertEqual(settings.chesscom_time_class, "bullet")

    def test_get_settings_applies_chesscom_blitz_profile_paths(self) -> None:
        settings = config.get_settings(source="chesscom", profile="blitz")

        self.assertTrue(
            settings.checkpoint_path.name.endswith("chesscom_since_blitz.txt")
        )
        self.assertTrue(
            settings.analysis_checkpoint_path.name.endswith(
                "analysis_checkpoint_chesscom_blitz.json"
            )
        )
        self.assertTrue(
            settings.fixture_pgn_path.name.endswith("chesscom_blitz_sample.pgn")
        )
        self.assertEqual(settings.chesscom_time_class, "blitz")

    def test_get_settings_applies_chesscom_rapid_profile_paths(self) -> None:
        settings = config.get_settings(source="chesscom", profile="rapid")

        self.assertTrue(
            settings.checkpoint_path.name.endswith("chesscom_since_rapid.txt")
        )
        self.assertTrue(
            settings.analysis_checkpoint_path.name.endswith(
                "analysis_checkpoint_chesscom_rapid.json"
            )
        )
        self.assertTrue(
            settings.fixture_pgn_path.name.endswith("chesscom_rapid_sample.pgn")
        )
        self.assertEqual(settings.chesscom_time_class, "rapid")

    def test_get_settings_applies_chesscom_classical_profile_paths(self) -> None:
        settings = config.get_settings(source="chesscom", profile="classical")

        self.assertTrue(
            settings.checkpoint_path.name.endswith("chesscom_since_classical.txt")
        )
        self.assertTrue(
            settings.analysis_checkpoint_path.name.endswith(
                "analysis_checkpoint_chesscom_classical.json"
            )
        )
        self.assertTrue(
            settings.fixture_pgn_path.name.endswith("chesscom_classical_sample.pgn")
        )
        self.assertEqual(settings.chesscom_time_class, "classical")


if __name__ == "__main__":
    unittest.main()
