import logging
import unittest

from tactix.utils.logger import get_logger, set_level


class LoggingUtilsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.logger = logging.getLogger("tactix")
        self.original_handlers = list(self.logger.handlers)
        self.original_level = self.logger.level

    def tearDown(self) -> None:
        self.logger.handlers = list(self.original_handlers)
        self.logger.setLevel(self.original_level)

    def test_get_logger_reuses_existing_handlers(self) -> None:
        handler = logging.StreamHandler()
        self.logger.handlers = [handler]

        logger = get_logger("tactix")

        self.assertIs(logger, self.logger)
        self.assertEqual(len(logger.handlers), 1)

    def test_set_level_updates_known_loggers(self) -> None:
        set_level(logging.WARNING)

        self.assertEqual(logging.getLogger("tactix").level, logging.WARNING)
        self.assertEqual(logging.getLogger("airflow").level, logging.WARNING)
        self.assertEqual(logging.getLogger("uvicorn").level, logging.WARNING)


if __name__ == "__main__":
    unittest.main()
