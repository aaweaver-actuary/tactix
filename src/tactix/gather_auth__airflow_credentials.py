from __future__ import annotations

from tactix.config import Settings


def gather_auth__airflow_credentials(settings: Settings) -> tuple[str, str] | None:
    """Retrieve Airflow authentication credentials from settings.

    Args:
        settings: Application settings containing Airflow credentials.

    Returns:
        Tuple of (username, password) if both are set; otherwise, None.
    """
    if not settings.airflow_username or not settings.airflow_password:
        return None
    return (settings.airflow_username, settings.airflow_password)
