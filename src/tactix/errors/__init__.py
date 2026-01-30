import requests


class RateLimitError(requests.HTTPError):
    """HTTP rate limit error."""
