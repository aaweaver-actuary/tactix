import unittest

from tactix.models import PracticeAttemptRequest


class ModelsTests(unittest.TestCase):
    def test_practice_attempt_request_types(self) -> None:
        request = PracticeAttemptRequest(
            tactic_id=123,
            position_id=456,
            attempted_uci="e2e4",
            source="lichess",
            served_at_ms=789,
        )

        self.assertIsInstance(request.tactic_id, int)
        self.assertIsInstance(request.position_id, int)
        self.assertIsInstance(request.attempted_uci, str)
        self.assertIsInstance(request.source, (str, type(None)))
        self.assertIsInstance(request.served_at_ms, int)


if __name__ == "__main__":
    unittest.main()
