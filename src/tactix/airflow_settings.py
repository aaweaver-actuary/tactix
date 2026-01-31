import os
from dataclasses import dataclass


@dataclass(slots=True)
class AirflowSettings:
    """Airflow-specific configuration."""

    base_url: str = os.getenv("TACTIX_AIRFLOW_URL", "").strip()
    username: str = os.getenv("TACTIX_AIRFLOW_USERNAME", "admin").strip()
    password: str = os.getenv("TACTIX_AIRFLOW_PASSWORD", "admin").strip()
    enabled: bool = os.getenv("TACTIX_AIRFLOW_ENABLED", "0") == "1"
    api_timeout_s: int = int(os.getenv("TACTIX_AIRFLOW_TIMEOUT_S", "15"))
    poll_interval_s: int = int(os.getenv("TACTIX_AIRFLOW_POLL_INTERVAL_S", "5"))
    poll_timeout_s: int = int(os.getenv("TACTIX_AIRFLOW_POLL_TIMEOUT_S", "600"))
