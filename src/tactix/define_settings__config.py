"""Define top-level application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from pathlib import Path

from tactix.airflow_settings import AirflowSettings
from tactix.apply_settings_aliases__config import _apply_settings_aliases
from tactix.define_chesscom_settings__config import ChesscomSettings
from tactix.define_config_defaults__config import (
    _MISSING,
    _STOCKFISH_PROFILE_DEPTHS,
    DEFAULT_CHESSCOM_ANALYSIS_CHECKPOINT,
    DEFAULT_CHESSCOM_FIXTURE,
    DEFAULT_DATA_DIR,
    DEFAULT_LICHESS_ANALYSIS_CHECKPOINT,
    DEFAULT_LICHESS_CHECKPOINT,
    DEFAULT_LICHESS_FIXTURE,
)
from tactix.define_lichess_settings__config import LichessSettings
from tactix.define_stockfish_settings__config import StockfishSettings
from tactix.PostgresSettings import PostgresSettings
from tactix.raise_on_unexpected_kwargs__config import _raise_on_unexpected_kwargs
from tactix.read_fork_severity_floor__config import _read_fork_severity_floor
from tactix.resolve_field_value__config import _field_value


def _normalize_source_value(source: str) -> str:
    return (source or "").strip().lower() or "lichess"


def _default_user_value() -> str:
    return os.getenv(
        "TACTIX_USER",
        os.getenv("LICHESS_USERNAME", os.getenv("LICHESS_USER", "lichess")),
    )


def _normalize_profile_value(profile: str | None) -> str:
    return (profile or "").strip().lower()


def _chesscom_time_class_from_profile(profile: str) -> str:
    if profile == "correspondence":
        return "daily"
    return profile


@dataclass(slots=True, init=False)
# pylint: disable=too-many-public-methods,missing-function-docstring,too-many-instance-attributes
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
    checkpoint_path: Path = DEFAULT_LICHESS_CHECKPOINT
    analysis_checkpoint_path: Path = DEFAULT_LICHESS_ANALYSIS_CHECKPOINT
    fixture_pgn_path: Path = DEFAULT_LICHESS_FIXTURE
    use_fixture_when_no_token: bool = False
    chesscom_fixture_pgn_path: Path = DEFAULT_CHESSCOM_FIXTURE
    chesscom_use_fixture_when_no_token: bool = False
    _stockfish_path_overridden: bool = False

    def __init__(self, **kwargs: object) -> None:
        for field_info in fields(self):
            name = field_info.name
            setattr(self, name, _field_value(name, field_info, kwargs))
        _apply_settings_aliases(self, kwargs)
        self._apply_compat_kwargs(kwargs)
        _raise_on_unexpected_kwargs(kwargs)

    def _apply_compat_kwargs(self, kwargs: dict[str, object]) -> None:
        compat_fields = (
            "checkpoint_path",
            "analysis_checkpoint_path",
            "fixture_pgn_path",
            "use_fixture_when_no_token",
            "chesscom_fixture_pgn_path",
            "chesscom_use_fixture_when_no_token",
            "lichess_profile",
            "lichess_token_cache_path",
            "airflow_base_url",
            "airflow_username",
            "airflow_password",
            "airflow_api_timeout_s",
            "airflow_poll_interval_s",
            "airflow_poll_timeout_s",
            "airflow_enabled",
            "postgres_dsn",
            "postgres_host",
            "postgres_port",
            "postgres_db",
            "postgres_user",
            "postgres_password",
            "postgres_sslmode",
            "postgres_connect_timeout_s",
            "postgres_analysis_enabled",
            "postgres_pgns_enabled",
        )
        for name in compat_fields:
            value = kwargs.pop(name, _MISSING)
            if value is not _MISSING:
                setattr(self, name, value)

    def apply_source_defaults(self) -> None:
        source = _normalize_source_value(self.source)
        self.source = source
        default_user = _default_user_value()
        if source == "chesscom":
            self._apply_source_defaults__chesscom(default_user)
            return
        self._apply_source_defaults__lichess(default_user)

    def apply_lichess_profile(self, profile: str | None = None) -> None:
        if self.source != "lichess":
            return
        profile_value = (profile or self.lichess_profile or "").strip()
        if not profile_value:
            return
        normalized = profile_value.lower()
        self.lichess_profile = normalized
        self.apply_stockfish_profile(normalized)
        self.checkpoint_path = self.checkpoint_path.with_name(f"lichess_since_{normalized}.txt")
        self.analysis_checkpoint_path = self.analysis_checkpoint_path.with_name(
            f"analysis_checkpoint_lichess_{normalized}.json"
        )
        self.fixture_pgn_path = self.fixture_pgn_path.with_name(f"lichess_{normalized}_sample.pgn")

    def apply_chesscom_profile(self, profile: str | None = None) -> None:
        if self.source != "chesscom":
            return
        normalized = _normalize_profile_value(profile or self.chesscom_profile)
        if not normalized:
            return
        self.chesscom_profile = normalized
        self.apply_stockfish_profile(normalized)
        self._apply_chesscom_profile_paths(normalized)

    def apply_stockfish_profile(self, profile: str | None = None) -> None:
        profile_value = (profile or "").strip().lower()
        if not profile_value:
            return
        if self.stockfish_depth is None:
            depth = _STOCKFISH_PROFILE_DEPTHS.get(profile_value)
            if depth is not None:
                self.stockfish_depth = depth

    def _apply_source_defaults__chesscom(self, default_user: str) -> None:
        if self.user == default_user:
            self.user = self.chesscom.user
        if self.checkpoint_path == DEFAULT_LICHESS_CHECKPOINT:
            self.checkpoint_path = self.chesscom.checkpoint_path
        if self.analysis_checkpoint_path == DEFAULT_LICHESS_ANALYSIS_CHECKPOINT:
            self.analysis_checkpoint_path = DEFAULT_CHESSCOM_ANALYSIS_CHECKPOINT

    def _apply_source_defaults__lichess(self, default_user: str) -> None:
        if self.user == default_user:
            self.user = self.lichess.user
        if self.checkpoint_path == self.chesscom.checkpoint_path:
            self.checkpoint_path = DEFAULT_LICHESS_CHECKPOINT
        if self.analysis_checkpoint_path == DEFAULT_CHESSCOM_ANALYSIS_CHECKPOINT:
            self.analysis_checkpoint_path = DEFAULT_LICHESS_ANALYSIS_CHECKPOINT

    def _apply_chesscom_profile_paths(self, normalized: str) -> None:
        self.chesscom_time_class = _chesscom_time_class_from_profile(normalized)
        self.checkpoint_path = self.checkpoint_path.with_name(f"chesscom_since_{normalized}.txt")
        self.analysis_checkpoint_path = self.analysis_checkpoint_path.with_name(
            f"analysis_checkpoint_chesscom_{normalized}.json"
        )
        self.fixture_pgn_path = self.fixture_pgn_path.with_name(f"chesscom_{normalized}_sample.pgn")
        self.chesscom_fixture_pgn_path = self.chesscom_fixture_pgn_path.with_name(
            f"chesscom_{normalized}_sample.pgn"
        )

    @property
    def data_dir(self) -> Path:
        return self.duckdb_path.parent

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_version_file.parent.mkdir(parents=True, exist_ok=True)
        if self.analysis_checkpoint_path is not None:
            self.analysis_checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def lichess_profile(self) -> str:
        return self.lichess.profile

    @lichess_profile.setter
    def lichess_profile(self, value: str) -> None:
        self.lichess.profile = value

    @property
    def chesscom_profile(self) -> str:
        return self.chesscom.profile

    @chesscom_profile.setter
    def chesscom_profile(self, value: str) -> None:
        self.chesscom.profile = value

    @property
    def lichess_token_cache_path(self) -> Path:
        return self.lichess.token_cache_path

    @lichess_token_cache_path.setter
    def lichess_token_cache_path(self, value: Path) -> None:
        self.lichess.token_cache_path = value

    @property
    def airflow_base_url(self) -> str:
        return self.airflow.base_url

    @airflow_base_url.setter
    def airflow_base_url(self, value: str) -> None:
        self.airflow.base_url = value

    @property
    def airflow_username(self) -> str:
        return self.airflow.username

    @airflow_username.setter
    def airflow_username(self, value: str) -> None:
        self.airflow.username = value

    @property
    def airflow_password(self) -> str:
        return self.airflow.password

    @airflow_password.setter
    def airflow_password(self, value: str) -> None:
        self.airflow.password = value

    @property
    def airflow_api_timeout_s(self) -> int:
        return self.airflow.api_timeout_s

    @airflow_api_timeout_s.setter
    def airflow_api_timeout_s(self, value: int) -> None:
        self.airflow.api_timeout_s = value

    @property
    def airflow_poll_interval_s(self) -> int:
        return self.airflow.poll_interval_s

    @airflow_poll_interval_s.setter
    def airflow_poll_interval_s(self, value: int) -> None:
        self.airflow.poll_interval_s = value

    @property
    def airflow_poll_timeout_s(self) -> int:
        return self.airflow.poll_timeout_s

    @airflow_poll_timeout_s.setter
    def airflow_poll_timeout_s(self, value: int) -> None:
        self.airflow.poll_timeout_s = value

    @property
    def airflow_enabled(self) -> bool:
        return self.airflow.enabled

    @airflow_enabled.setter
    def airflow_enabled(self, value: bool) -> None:
        self.airflow.enabled = value

    @property
    def postgres_dsn(self) -> str | None:
        return self.postgres.dsn

    @postgres_dsn.setter
    def postgres_dsn(self, value: str | None) -> None:
        self.postgres.dsn = value

    @property
    def postgres_host(self) -> str | None:
        return self.postgres.host

    @postgres_host.setter
    def postgres_host(self, value: str | None) -> None:
        self.postgres.host = value

    @property
    def postgres_port(self) -> int:
        return self.postgres.port

    @postgres_port.setter
    def postgres_port(self, value: int) -> None:
        self.postgres.port = value

    @property
    def postgres_db(self) -> str | None:
        return self.postgres.db

    @postgres_db.setter
    def postgres_db(self, value: str | None) -> None:
        self.postgres.db = value

    @property
    def postgres_user(self) -> str | None:
        return self.postgres.user

    @postgres_user.setter
    def postgres_user(self, value: str | None) -> None:
        self.postgres.user = value

    @property
    def postgres_password(self) -> str | None:
        return self.postgres.password

    @postgres_password.setter
    def postgres_password(self, value: str | None) -> None:
        self.postgres.password = value

    @property
    def postgres_sslmode(self) -> str:
        return self.postgres.sslmode

    @postgres_sslmode.setter
    def postgres_sslmode(self, value: str) -> None:
        self.postgres.sslmode = value

    @property
    def postgres_connect_timeout_s(self) -> int:
        return self.postgres.connect_timeout_s

    @postgres_connect_timeout_s.setter
    def postgres_connect_timeout_s(self, value: int) -> None:
        self.postgres.connect_timeout_s = value

    @property
    def postgres_analysis_enabled(self) -> bool:
        return self.postgres.analysis_enabled

    @postgres_analysis_enabled.setter
    def postgres_analysis_enabled(self, value: bool) -> None:
        self.postgres.analysis_enabled = value

    @property
    def postgres_pgns_enabled(self) -> bool:
        return self.postgres.pgns_enabled

    @postgres_pgns_enabled.setter
    def postgres_pgns_enabled(self, value: bool) -> None:
        self.postgres.pgns_enabled = value

    @property
    def lichess_user(self) -> str:
        return self.lichess.user

    @lichess_user.setter
    def lichess_user(self, value: str) -> None:
        self.lichess.user = value

    @property
    def lichess_token(self) -> str | None:
        return self.lichess.token

    @lichess_token.setter
    def lichess_token(self, value: str | None) -> None:
        self.lichess.token = value

    @property
    def lichess_oauth_client_id(self) -> str | None:
        return self.lichess.oauth_client_id

    @lichess_oauth_client_id.setter
    def lichess_oauth_client_id(self, value: str | None) -> None:
        self.lichess.oauth_client_id = value

    @property
    def lichess_oauth_client_secret(self) -> str | None:
        return self.lichess.oauth_client_secret

    @lichess_oauth_client_secret.setter
    def lichess_oauth_client_secret(self, value: str | None) -> None:
        self.lichess.oauth_client_secret = value

    @property
    def lichess_oauth_refresh_token(self) -> str | None:
        return self.lichess.oauth_refresh_token

    @lichess_oauth_refresh_token.setter
    def lichess_oauth_refresh_token(self, value: str | None) -> None:
        self.lichess.oauth_refresh_token = value

    @property
    def lichess_oauth_token_url(self) -> str:
        return self.lichess.oauth_token_url

    @lichess_oauth_token_url.setter
    def lichess_oauth_token_url(self, value: str) -> None:
        self.lichess.oauth_token_url = value

    @property
    def chesscom_user(self) -> str:
        return self.chesscom.user

    @chesscom_user.setter
    def chesscom_user(self, value: str) -> None:
        self.chesscom.user = value

    @property
    def chesscom_token(self) -> str | None:
        return self.chesscom.token

    @chesscom_token.setter
    def chesscom_token(self, value: str | None) -> None:
        self.chesscom.token = value

    @property
    def chesscom_time_class(self) -> str:
        return self.chesscom.time_class

    @chesscom_time_class.setter
    def chesscom_time_class(self, value: str) -> None:
        self.chesscom.time_class = value

    @property
    def chesscom_max_retries(self) -> int:
        return self.chesscom.max_retries

    @chesscom_max_retries.setter
    def chesscom_max_retries(self, value: int) -> None:
        self.chesscom.max_retries = value

    @property
    def chesscom_retry_backoff_ms(self) -> int:
        return self.chesscom.retry_backoff_ms

    @chesscom_retry_backoff_ms.setter
    def chesscom_retry_backoff_ms(self, value: int) -> None:
        self.chesscom.retry_backoff_ms = value

    @property
    def chesscom_checkpoint_path(self) -> Path:
        return self.chesscom.checkpoint_path

    @chesscom_checkpoint_path.setter
    def chesscom_checkpoint_path(self, value: Path) -> None:
        self.chesscom.checkpoint_path = value

    @property
    def stockfish_path(self) -> Path:
        return self.stockfish.path

    @stockfish_path.setter
    def stockfish_path(self, value: Path) -> None:
        self.stockfish.path = value
        self._stockfish_path_overridden = True

    @property
    def stockfish_checksum(self) -> str | None:
        return self.stockfish.checksum

    @stockfish_checksum.setter
    def stockfish_checksum(self, value: str | None) -> None:
        self.stockfish.checksum = value

    @property
    def stockfish_checksum_mode(self) -> str:
        return self.stockfish.checksum_mode

    @stockfish_checksum_mode.setter
    def stockfish_checksum_mode(self, value: str) -> None:
        self.stockfish.checksum_mode = value

    @property
    def stockfish_threads(self) -> int:
        return self.stockfish.threads

    @stockfish_threads.setter
    def stockfish_threads(self, value: int) -> None:
        self.stockfish.threads = value

    @property
    def stockfish_hash_mb(self) -> int:
        return self.stockfish.hash_mb

    @stockfish_hash_mb.setter
    def stockfish_hash_mb(self, value: int) -> None:
        self.stockfish.hash_mb = value

    @property
    def stockfish_movetime_ms(self) -> int:
        return self.stockfish.movetime_ms

    @stockfish_movetime_ms.setter
    def stockfish_movetime_ms(self, value: int) -> None:
        self.stockfish.movetime_ms = value

    @property
    def stockfish_depth(self) -> int | None:
        return self.stockfish.depth

    @stockfish_depth.setter
    def stockfish_depth(self, value: int | None) -> None:
        self.stockfish.depth = value

    @property
    def stockfish_multipv(self) -> int:
        return self.stockfish.multipv

    @stockfish_multipv.setter
    def stockfish_multipv(self, value: int) -> None:
        self.stockfish.multipv = value

    @property
    def stockfish_skill_level(self) -> int:
        return self.stockfish.skill_level

    @stockfish_skill_level.setter
    def stockfish_skill_level(self, value: int) -> None:
        self.stockfish.skill_level = value

    @property
    def stockfish_limit_strength(self) -> bool:
        return self.stockfish.limit_strength

    @stockfish_limit_strength.setter
    def stockfish_limit_strength(self, value: bool) -> None:
        self.stockfish.limit_strength = value

    @property
    def stockfish_uci_elo(self) -> int | None:
        return self.stockfish.uci_elo

    @stockfish_uci_elo.setter
    def stockfish_uci_elo(self, value: int | None) -> None:
        self.stockfish.uci_elo = value

    @property
    def stockfish_uci_analyse_mode(self) -> bool:
        return self.stockfish.uci_analyse_mode

    @stockfish_uci_analyse_mode.setter
    def stockfish_uci_analyse_mode(self, value: bool) -> None:
        self.stockfish.uci_analyse_mode = value

    @property
    def stockfish_use_nnue(self) -> bool:
        return self.stockfish.use_nnue

    @stockfish_use_nnue.setter
    def stockfish_use_nnue(self, value: bool) -> None:
        self.stockfish.use_nnue = value

    @property
    def stockfish_ponder(self) -> bool:
        return self.stockfish.ponder

    @stockfish_ponder.setter
    def stockfish_ponder(self, value: bool) -> None:
        self.stockfish.ponder = value

    @property
    def stockfish_random_seed(self) -> int | None:
        return self.stockfish.random_seed

    @stockfish_random_seed.setter
    def stockfish_random_seed(self, value: int | None) -> None:
        self.stockfish.random_seed = value

    @property
    def stockfish_max_retries(self) -> int:
        return self.stockfish.max_retries

    @stockfish_max_retries.setter
    def stockfish_max_retries(self, value: int) -> None:
        self.stockfish.max_retries = value

    @property
    def stockfish_retry_backoff_ms(self) -> int:
        return self.stockfish.retry_backoff_ms

    @stockfish_retry_backoff_ms.setter
    def stockfish_retry_backoff_ms(self, value: int) -> None:
        self.stockfish.retry_backoff_ms = value
