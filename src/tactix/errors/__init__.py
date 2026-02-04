# pylint: disable=duplicate-code,R0801
"""Custom error types used in tactix."""

import requests


class RateLimitError(requests.HTTPError):
    """HTTP rate limit error."""
