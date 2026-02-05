"""Regular expression patterns for PGN site IDs."""

from __future__ import annotations

# pylint: disable=invalid-name
import re

SITE_PATTERNS = [
    re.compile(r"https?://lichess\.org/([A-Za-z0-9]+)"),
    re.compile(r"https?://(?:www\.)?chess\.com/game/(?:live|daily|archive|analysis)/([0-9]+)"),
    re.compile(r"https?://(?:www\.)?chess\.com/game/([0-9]+)"),
]

__all__ = ["SITE_PATTERNS"]