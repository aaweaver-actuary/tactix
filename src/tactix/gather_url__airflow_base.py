from __future__ import annotations

from tactix.config import Settings


def gather_url__airflow_base(settings: Settings) -> str:
    """Return the Airflow base URL without any trailing slash.

    Args:
        settings: Application settings containing `airflow_base_url`.

    Returns:
        The base URL string with trailing "/" characters removed.
    """
    return settings.airflow_base_url.rstrip("/")
