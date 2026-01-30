from __future__ import annotations


def _apply_airflow_optional_conf(conf: dict[str, object], key: str, value: int | None) -> None:
    if value is not None:
        conf[key] = value
