import unittest

from tactix.db._rating_bucket_clause import _rating_bucket_clause


class RatingBucketClauseTests(unittest.TestCase):
    def test_unknown_bucket(self) -> None:
        self.assertEqual(_rating_bucket_clause("unknown"), "r.user_rating IS NULL")

    def test_lower_bucket(self) -> None:
        self.assertEqual(
            _rating_bucket_clause("< 1200"),
            "r.user_rating IS NOT NULL AND r.user_rating < 1200",
        )

    def test_range_bucket(self) -> None:
        self.assertEqual(
            _rating_bucket_clause("1000-1199"),
            "r.user_rating >= 1000 AND r.user_rating <= 1199",
        )

    def test_upper_bucket(self) -> None:
        self.assertEqual(
            _rating_bucket_clause("1600+"),
            "r.user_rating >= 1600",
        )

    def test_invalid_bucket_falls_back(self) -> None:
        self.assertEqual(_rating_bucket_clause("abc"), "r.user_rating IS NULL")
