from __future__ import annotations

from tactix.apply_airflow_optional_conf__airflow_jobs import _apply_airflow_optional_conf


def _airflow_conf(
    source: str | None,
    profile: str | None,
    backfill_start_ms: int | None = None,
    backfill_end_ms: int | None = None,
    triggered_at_ms: int | None = None,
) -> dict[str, object]:
    conf: dict[str, object] = {}
    if source:
        conf["source"] = source
    if profile:
        key = "chesscom_profile" if source == "chesscom" else "lichess_profile"
        conf[key] = profile
    _apply_airflow_optional_conf(conf, "backfill_start_ms", backfill_start_ms)
    _apply_airflow_optional_conf(conf, "backfill_end_ms", backfill_end_ms)
    _apply_airflow_optional_conf(conf, "triggered_at_ms", triggered_at_ms)
    return conf
