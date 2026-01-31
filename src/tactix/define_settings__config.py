from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from tactix.airflow_settings import AirflowSettings
from tactix.apply_settings_aliases__config import _apply_settings_aliases
from tactix.define_chesscom_settings__config import ChesscomSettings
from tactix.define_config_defaults__config import (
    _STOCKFISH_PROFILE_DEPTHS,
    DEFAULT_DATA_DIR,
)
from tactix.define_lichess_settings__config import LichessSettings
from tactix.define_stockfish_settings__config import StockfishSettings
from tactix.PostgresSettings import PostgresSettings
from tactix.raise_on_unexpected_kwargs__config import _raise_on_unexpected_kwargs
from tactix.read_fork_severity_floor__config import _read_fork_severity_floor
from tactix.resolve_field_value__config import _field_value


@dataclass(slots=True, init=False)
class Settings:
    """Central configuration for ingestion, analysis, and UI refresh."""

    api_token: str = os.getenv("TACTIX_API_TOKEN", "local-dev-token")
    user: str = os.getenv(
        "TACTIX_USER",
        os.getenv("LICHESS_USERNAME", os.getenv("LICHESS_USER", "lichess")),
    )
    source: str = os.getenv("TACTIX_SOURCE", "lichess")

    lichess: LichessSettings = field(default_factory=LichessSettings)
    chesscom: ChesscomSettings = field(default_factory=ChesscomSettings)

    stockfish: StockfishSettings = field(default_factory=StockfishSettings)
    postgres: PostgresSettings = field(default_factory=PostgresSettings)
    airflow: AirflowSettings = field(default_factory=AirflowSettings)

    duckdb_path: Path = Path(os.getenv("TACTIX_DUCKDB_PATH", DEFAULT_DATA_DIR / "tactix.duckdb"))
    fork_severity_floor: float | None = _read_fork_severity_floor()
    metrics_version_file: Path = Path(
        os.getenv("TACTIX_METRICS_VERSION_PATH", DEFAULT_DATA_DIR / "metrics_version.txt")
    )
    rapid_perf: str = os.getenv("TACTIX_PERF", "rapid")
    run_context: str = os.getenv("TACTIX_RUN_CONTEXT", "app")

    def __init__(self, **kwargs: object) -> None:
        for name, field_info in self.__dataclass_fields__.items():
            setattr(self, name, _field_value(name, field_info, kwargs))
        _apply_settings_aliases(self, kwargs)
        _raise_on_unexpected_kwargs(kwargs)

    def apply_stockfish_profile(self, profile: str | None = None) -> None:
        profile_value = (profile or "").strip().lower()
        if not profile_value:
            return
        if self.stockfish_depth is None:
            depth = _STOCKFISH_PROFILE_DEPTHS.get(profile_value)
            if depth is not None:
                self.stockfish_depth = depth

    @property
    def data_dir(self) -> Path:
        return self.duckdb_path.parent

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_version_file.parent.mkdir(parents=True, exist_ok=True)
        self.analysis_checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
