def _clock_to_seconds(hours: str, minutes: str, seconds: str) -> float | None:
    try:
        return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
    except ValueError:
        return None
