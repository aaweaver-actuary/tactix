from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from tactix.apply_settings_aliases__config import _apply_settings_aliases
from tactix.define_chesscom_settings__config import ChesscomSettings
from tactix.define_config_defaults__config import (
    _STOCKFISH_PROFILE_DEPTHS,
    DEFAULT_CHESSCOM_ANALYSIS_CHECKPOINT,
    DEFAULT_CHESSCOM_CHECKPOINT,
    DEFAULT_CHESSCOM_FIXTURE,
    DEFAULT_DATA_DIR,
    DEFAULT_LICHESS_ANALYSIS_CHECKPOINT,
    DEFAULT_LICHESS_CHECKPOINT,
    DEFAULT_LICHESS_FIXTURE,
)
from tactix.define_lichess_settings__config import LichessSettings
from tactix.define_stockfish_settings__config import StockfishSettings
from tactix.raise_on_unexpected_kwargs__config import _raise_on_unexpected_kwargs
from tactix.read_fork_severity_floor__config import _read_fork_severity_floor
from tactix.resolve_field_value__config import _field_value


@dataclass(slots=True, init=False)
class Settings:
    """Central configuration for ingestion, analysis, and UI refresh."""

    if TYPE_CHECKING:
        lichess_user: str
        lichess_token: str | None
        lichess_oauth_client_id: str | None
        lichess_oauth_client_secret: str | None
        lichess_oauth_refresh_token: str | None
        lichess_oauth_token_url: str
        chesscom_user: str
        chesscom_token: str | None
        chesscom_time_class: str
        chesscom_profile: str
        chesscom_max_retries: int
        chesscom_retry_backoff_ms: int
        chesscom_checkpoint_path: Path

    api_token: str = os.getenv("TACTIX_API_TOKEN", "local-dev-token")
    user: str = os.getenv(
        "TACTIX_USER",
        os.getenv("LICHESS_USERNAME", os.getenv("LICHESS_USER", "lichess")),
    )
    source: str = os.getenv("TACTIX_SOURCE", "lichess")

    lichess: LichessSettings = field(default_factory=LichessSettings)
    chesscom: ChesscomSettings = field(default_factory=ChesscomSettings)

    stockfish: StockfishSettings = field(default_factory=StockfishSettings)

    duckdb_path: Path = Path(os.getenv("TACTIX_DUCKDB_PATH", DEFAULT_DATA_DIR / "tactix.duckdb"))
    checkpoint_path: Path = Path(os.getenv("TACTIX_CHECKPOINT_PATH", DEFAULT_LICHESS_CHECKPOINT))
    analysis_checkpoint_path: Path = Path(
        os.getenv(
            "TACTIX_ANALYSIS_CHECKPOINT_PATH",
            DEFAULT_LICHESS_ANALYSIS_CHECKPOINT,
        )
    )
    fork_severity_floor: float | None = _read_fork_severity_floor()
    metrics_version_file: Path = Path(
        os.getenv("TACTIX_METRICS_VERSION_PATH", DEFAULT_DATA_DIR / "metrics_version.txt")
    )
    rapid_perf: str = os.getenv("TACTIX_PERF", "rapid")
    lichess_profile: str = os.getenv("TACTIX_LICHESS_PROFILE", "")
    fixture_pgn_path: Path = Path(os.getenv("TACTIX_FIXTURE_PGN_PATH", DEFAULT_LICHESS_FIXTURE))
    chesscom_fixture_pgn_path: Path = Path(
        os.getenv(
            "TACTIX_CHESSCOM_FIXTURE_PGN_PATH",
            DEFAULT_CHESSCOM_FIXTURE,
        )
    )
    use_fixture_when_no_token: bool = os.getenv("TACTIX_USE_FIXTURE", "1") == "1"
    chesscom_use_fixture_when_no_token: bool = os.getenv("TACTIX_CHESSCOM_USE_FIXTURE", "1") == "1"
    lichess_token_cache_path: Path = Path(
        os.getenv("LICHESS_TOKEN_CACHE_PATH", DEFAULT_DATA_DIR / "lichess_token.json")
    )
    airflow_base_url: str = os.getenv("TACTIX_AIRFLOW_URL", "").strip()
    airflow_username: str = os.getenv("TACTIX_AIRFLOW_USERNAME", "admin").strip()
    airflow_password: str = os.getenv("TACTIX_AIRFLOW_PASSWORD", "admin").strip()
    airflow_enabled: bool = os.getenv("TACTIX_AIRFLOW_ENABLED", "0") == "1"
    airflow_api_timeout_s: int = int(os.getenv("TACTIX_AIRFLOW_TIMEOUT_S", "15"))
    airflow_poll_interval_s: int = int(os.getenv("TACTIX_AIRFLOW_POLL_INTERVAL_S", "5"))
    airflow_poll_timeout_s: int = int(os.getenv("TACTIX_AIRFLOW_POLL_TIMEOUT_S", "600"))
    postgres_dsn: str | None = os.getenv("TACTIX_POSTGRES_DSN")
    postgres_host: str | None = os.getenv("TACTIX_POSTGRES_HOST")
    postgres_port: int = int(os.getenv("TACTIX_POSTGRES_PORT", "5432"))
    postgres_db: str | None = os.getenv("TACTIX_POSTGRES_DB")
    postgres_user: str | None = os.getenv("TACTIX_POSTGRES_USER")
    postgres_password: str | None = os.getenv("TACTIX_POSTGRES_PASSWORD")
    postgres_sslmode: str = os.getenv("TACTIX_POSTGRES_SSLMODE", "disable")
    postgres_connect_timeout_s: int = int(os.getenv("TACTIX_POSTGRES_CONNECT_TIMEOUT", "5"))
    postgres_analysis_enabled: bool = os.getenv("TACTIX_POSTGRES_ANALYSIS_ENABLED", "1") == "1"
    postgres_pgns_enabled: bool = os.getenv("TACTIX_POSTGRES_PGNS_ENABLED", "1") == "1"
    run_context: str = os.getenv("TACTIX_RUN_CONTEXT", "app")

    def __init__(self, **kwargs: object) -> None:
        for name, field_info in self.__dataclass_fields__.items():
            setattr(self, name, _field_value(name, field_info, kwargs))
        _apply_settings_aliases(self, kwargs)
        _raise_on_unexpected_kwargs(kwargs)

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
    def chesscom_profile(self) -> str:
        return self.chesscom.profile

    @chesscom_profile.setter
    def chesscom_profile(self, value: str) -> None:
        self.chesscom.profile = value

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
    def stockfish_path(self, value: Path | str) -> None:
        self.stockfish.path = Path(value)

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

    def apply_source_defaults(self) -> None:
        self.source = (self.source or "lichess").lower()
        if self.source == "chesscom":
            self._apply_chesscom_source_defaults()
            return
        if not self.user:
            self.user = self.lichess_user
        if self.source == "lichess":
            self._apply_lichess_source_defaults()

    def _apply_chesscom_source_defaults(self) -> None:
        self.user = self.chesscom_user
        if not self.chesscom_profile:
            self.chesscom_profile = self._infer_chesscom_profile()
        self.checkpoint_path = self.chesscom_checkpoint_path
        self.analysis_checkpoint_path = self.data_dir / "analysis_checkpoint_chesscom.json"
        self.fixture_pgn_path = self.chesscom_fixture_pgn_path
        self.use_fixture_when_no_token = self.chesscom_use_fixture_when_no_token
        self.apply_chesscom_profile()

    def _apply_lichess_source_defaults(self) -> None:
        self.analysis_checkpoint_path = self.data_dir / "analysis_checkpoint_lichess.json"
        self.apply_lichess_profile()

    def _infer_chesscom_profile(self) -> str:
        inferred_profile = (
            "correspondence" if self.chesscom_time_class == "daily" else self.chesscom_time_class
        )
        return inferred_profile or "blitz"

    @staticmethod
    def _normalize_profile_value(profile: str | None, fallback: str | None) -> str | None:
        profile_value = (profile or fallback or "").strip()
        return profile_value or None

    @staticmethod
    def _chesscom_time_class(profile_value: str) -> str:
        return "daily" if profile_value == "correspondence" else profile_value

    def apply_chesscom_profile(self, profile: str | None = None) -> None:
        profile_value = self._normalize_profile_value(profile, self.chesscom_profile)
        if not profile_value or self.source != "chesscom":
            return
        self.chesscom_profile = profile_value
        self.chesscom_time_class = self._chesscom_time_class(profile_value)
        self.apply_stockfish_profile(profile_value)
        self._apply_chesscom_checkpoint_paths(profile_value)
        self._apply_chesscom_analysis_checkpoint(profile_value)
        self._apply_chesscom_fixture_paths(profile_value)

    @staticmethod
    def _is_default_chesscom_checkpoint(
        checkpoint: Path,
        default_checkpoint: Path,
        default_name: str,
        *,
        include_default_constant: bool = False,
    ) -> bool:
        allowed_defaults = {default_checkpoint}
        if include_default_constant:
            allowed_defaults.add(DEFAULT_CHESSCOM_CHECKPOINT)
        return (
            checkpoint in allowed_defaults
            or checkpoint.name == default_name
            or checkpoint.name.startswith("chesscom_since_")
        )

    @staticmethod
    def _is_default_chesscom_analysis_checkpoint(
        checkpoint: Path,
        default_checkpoint: Path,
        default_name: str,
    ) -> bool:
        return (
            checkpoint in {DEFAULT_CHESSCOM_ANALYSIS_CHECKPOINT, default_checkpoint}
            or checkpoint.name == default_name
            or checkpoint.name.startswith("analysis_checkpoint_chesscom_")
        )

    @staticmethod
    def _is_chesscom_fixture_path(path: Path) -> bool:
        return path == DEFAULT_CHESSCOM_FIXTURE or (
            path.name.startswith("chesscom_") and path.name.endswith("_sample.pgn")
        )

    def _apply_chesscom_checkpoint_paths(self, profile_value: str) -> None:
        default_checkpoint = self.data_dir / "chesscom_since.txt"
        default_checkpoint_name = "chesscom_since.txt"
        profile_checkpoint = self.data_dir / f"chesscom_since_{profile_value}.txt"
        if self._is_default_chesscom_checkpoint(
            self.checkpoint_path,
            default_checkpoint,
            default_checkpoint_name,
        ):
            self.checkpoint_path = profile_checkpoint
        if self._is_default_chesscom_checkpoint(
            self.chesscom_checkpoint_path,
            default_checkpoint,
            default_checkpoint_name,
            include_default_constant=True,
        ):
            self.chesscom_checkpoint_path = self.checkpoint_path

    def _apply_chesscom_analysis_checkpoint(self, profile_value: str) -> None:
        default_analysis = self.data_dir / "analysis_checkpoint_chesscom.json"
        default_analysis_name = "analysis_checkpoint_chesscom.json"
        profile_analysis = self.data_dir / f"analysis_checkpoint_chesscom_{profile_value}.json"
        if self._is_default_chesscom_analysis_checkpoint(
            self.analysis_checkpoint_path,
            default_analysis,
            default_analysis_name,
        ):
            self.analysis_checkpoint_path = profile_analysis

    def _apply_chesscom_fixture_paths(self, profile_value: str) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        candidate = repo_root / f"tests/fixtures/chesscom_{profile_value}_sample.pgn"
        if not candidate.exists():
            return
        if self._is_chesscom_fixture_path(self.chesscom_fixture_pgn_path):
            self.chesscom_fixture_pgn_path = candidate
        if self._is_chesscom_fixture_path(self.fixture_pgn_path):
            self.fixture_pgn_path = candidate

    @staticmethod
    def _is_default_lichess_checkpoint(
        checkpoint: Path,
        default_checkpoint: Path,
    ) -> bool:
        return checkpoint in {DEFAULT_LICHESS_CHECKPOINT, default_checkpoint}

    @staticmethod
    def _is_default_lichess_analysis_checkpoint(
        checkpoint: Path,
        default_analysis: Path,
    ) -> bool:
        return checkpoint in {DEFAULT_LICHESS_ANALYSIS_CHECKPOINT, default_analysis}

    def _apply_lichess_fixture_path(self, profile_value: str) -> None:
        if self.fixture_pgn_path != DEFAULT_LICHESS_FIXTURE:
            return
        repo_root = Path(__file__).resolve().parents[2]
        candidate = repo_root / f"tests/fixtures/lichess_{profile_value}_sample.pgn"
        if candidate.exists():
            self.fixture_pgn_path = candidate

    def apply_lichess_profile(self, profile: str | None = None) -> None:
        profile_value = self._normalize_profile_value(profile, self.lichess_profile)
        if not profile_value:
            return
        self.lichess_profile = profile_value
        self.rapid_perf = profile_value
        self.apply_stockfish_profile(profile_value)
        if self.source != "lichess":
            return
        self._apply_lichess_profile_paths(profile_value)

    def _apply_lichess_profile_paths(self, profile_value: str) -> None:
        default_checkpoint = self.data_dir / "lichess_since.txt"
        if self._is_default_lichess_checkpoint(self.checkpoint_path, default_checkpoint):
            self.checkpoint_path = self.data_dir / f"lichess_since_{profile_value}.txt"
        default_analysis = self.data_dir / "analysis_checkpoint_lichess.json"
        if self._is_default_lichess_analysis_checkpoint(
            self.analysis_checkpoint_path,
            default_analysis,
        ):
            self.analysis_checkpoint_path = (
                self.data_dir / f"analysis_checkpoint_lichess_{profile_value}.json"
            )
        self._apply_lichess_fixture_path(profile_value)

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.chesscom_checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.metrics_version_file.parent.mkdir(parents=True, exist_ok=True)
        self.analysis_checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.lichess_token_cache_path.parent.mkdir(parents=True, exist_ok=True)
