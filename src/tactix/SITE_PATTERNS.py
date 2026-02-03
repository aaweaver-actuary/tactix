import re

SITE_PATTERNS = [
    re.compile(r"lichess\.org/([A-Za-z0-9]{8})"),
    re.compile(r"chess\.com/(?:game/live|game|live/game)/(\d+)", re.IGNORECASE),
    re.compile(r"chess\.com/.*/(\d{6,})", re.IGNORECASE),
]
