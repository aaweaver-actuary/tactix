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


if __name__ == "__main__":
    unittest.main()
