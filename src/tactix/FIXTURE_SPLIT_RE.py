"""Regex for splitting fixture payloads."""

# pylint: disable=invalid-name

import re

FIXTURE_SPLIT_RE: re.Pattern[str] = re.compile(r"\n{2,}(?=\[Event )")
