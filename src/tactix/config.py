from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


DEFAULT_DATA_DIR = Path(os.getenv("TACTIX_DATA_DIR", "data"))
DEFAULT_LICHESS_CHECKPOINT = DEFAULT_DATA_DIR / "lichess_since.txt"
DEFAULT_LICHESS_ANALYSIS_CHECKPOINT = (
    DEFAULT_DATA_DIR / "analysis_checkpoint_lichess.json"
)
DEFAULT_LICHESS_FIXTURE = Path("tests/fixtures/lichess_rapid_sample.pgn")
DEFAULT_CHESSCOM_CHECKPOINT = DEFAULT_DATA_DIR / "chesscom_since.txt"
DEFAULT_CHESSCOM_ANALYSIS_CHECKPOINT = (
    DEFAULT_DATA_DIR / "analysis_checkpoint_chesscom.json"
)
DEFAULT_CHESSCOM_FIXTURE = Path("tests/fixtures/chesscom_blitz_sample.pgn")
DEFAULT_BULLET_STOCKFISH_DEPTH = 8
DEFAULT_BLITZ_STOCKFISH_DEPTH = 10
DEFAULT_RAPID_STOCKFISH_DEPTH = 12
DEFAULT_CLASSICAL_STOCKFISH_DEPTH = 14
DEFAULT_CORRESPONDENCE_STOCKFISH_DEPTH = 16


def _read_fork_severity_floor() -> Optional[float]:
    value = os.getenv("TACTIX_FORK_SEVERITY_FLOOR")
    if not value:
        return None
    return float(value)


@dataclass(slots=True)
class Settings:
    """Central configuration for ingestion, analysis, and UI refresh."""

    api_token: str = os.getenv("TACTIX_API_TOKEN", "local-dev-token")
    user: str = os.getenv(
        "TACTIX_USER",
        os.getenv("LICHESS_USERNAME", os.getenv("LICHESS_USER", "lichess")),
    )
    lichess_user: str = os.getenv(
        "LICHESS_USERNAME", os.getenv("LICHESS_USER", "lichess")
    )
    source: str = os.getenv("TACTIX_SOURCE", "lichess")
    lichess_token: Optional[str] = os.getenv("LICHESS_TOKEN")
    lichess_oauth_client_id: Optional[str] = os.getenv("LICHESS_OAUTH_CLIENT_ID")
    lichess_oauth_client_secret: Optional[str] = os.getenv(
        "LICHESS_OAUTH_CLIENT_SECRET"
    )
    lichess_oauth_refresh_token: Optional[str] = os.getenv(
        "LICHESS_OAUTH_REFRESH_TOKEN"
    )
    lichess_oauth_token_url: str = os.getenv(
        "LICHESS_OAUTH_TOKEN_URL", "https://lichess.org/api/token"
    )
    chesscom_user: str = os.getenv(
        "CHESSCOM_USERNAME", os.getenv("CHESSCOM_USER", "chesscom")
    )
    chesscom_token: Optional[str] = os.getenv("CHESSCOM_TOKEN")
    chesscom_time_class: str = os.getenv("CHESSCOM_TIME_CLASS", "blitz")
    chesscom_profile: str = os.getenv("TACTIX_CHESSCOM_PROFILE", "")
    chesscom_max_retries: int = int(os.getenv("CHESSCOM_MAX_RETRIES", "3"))
    chesscom_retry_backoff_ms: int = int(os.getenv("CHESSCOM_RETRY_BACKOFF_MS", "500"))
    duckdb_path: Path = Path(
        os.getenv("TACTIX_DUCKDB_PATH", DEFAULT_DATA_DIR / "tactix.duckdb")
    )
    checkpoint_path: Path = Path(
        os.getenv("TACTIX_CHECKPOINT_PATH", DEFAULT_LICHESS_CHECKPOINT)
    )
    chesscom_checkpoint_path: Path = Path(
        os.getenv("TACTIX_CHESSCOM_CHECKPOINT_PATH", DEFAULT_CHESSCOM_CHECKPOINT)
    )
    analysis_checkpoint_path: Path = Path(
        os.getenv(
            "TACTIX_ANALYSIS_CHECKPOINT_PATH",
            DEFAULT_LICHESS_ANALYSIS_CHECKPOINT,
        )
    )
    stockfish_path: Path = Path(os.getenv("STOCKFISH_PATH", "stockfish"))
    stockfish_checksum: Optional[str] = os.getenv("STOCKFISH_SHA256") or os.getenv(
        "STOCKFISH_CHECKSUM"
    )
    stockfish_checksum_mode: str = os.getenv("STOCKFISH_CHECKSUM_MODE", "warn")
    stockfish_threads: int = int(os.getenv("STOCKFISH_THREADS", "1"))
    stockfish_hash_mb: int = int(os.getenv("STOCKFISH_HASH", "256"))
    stockfish_movetime_ms: int = int(os.getenv("STOCKFISH_MOVETIME_MS", "150"))
    stockfish_depth: Optional[int] = int(os.getenv("STOCKFISH_DEPTH", "0")) or None
    stockfish_multipv: int = int(os.getenv("STOCKFISH_MULTIPV", "3"))
    stockfish_skill_level: int = int(os.getenv("STOCKFISH_SKILL_LEVEL", "20"))
    stockfish_limit_strength: bool = os.getenv("STOCKFISH_LIMIT_STRENGTH", "0") == "1"
    stockfish_uci_elo: Optional[int] = int(os.getenv("STOCKFISH_UCI_ELO", "0")) or None
    stockfish_uci_analyse_mode: bool = (
        os.getenv("STOCKFISH_UCI_ANALYSE_MODE", "1") == "1"
    )
    stockfish_use_nnue: bool = os.getenv("STOCKFISH_USE_NNUE", "1") == "1"
    stockfish_ponder: bool = os.getenv("STOCKFISH_PONDER", "0") == "1"
    stockfish_random_seed: Optional[int] = (
        int(os.getenv("STOCKFISH_RANDOM_SEED", "0")) or None
    )
    stockfish_max_retries: int = int(os.getenv("STOCKFISH_MAX_RETRIES", "2"))
    stockfish_retry_backoff_ms: int = int(
        os.getenv("STOCKFISH_RETRY_BACKOFF_MS", "250")
    )
    fork_severity_floor: Optional[float] = _read_fork_severity_floor()
    metrics_version_file: Path = Path(
        os.getenv(
            "TACTIX_METRICS_VERSION_PATH", DEFAULT_DATA_DIR / "metrics_version.txt"
        )
    )
    rapid_perf: str = os.getenv("TACTIX_PERF", "rapid")
    lichess_profile: str = os.getenv("TACTIX_LICHESS_PROFILE", "")
    fixture_pgn_path: Path = Path(
        os.getenv("TACTIX_FIXTURE_PGN_PATH", DEFAULT_LICHESS_FIXTURE)
    )
    chesscom_fixture_pgn_path: Path = Path(
        os.getenv(
            "TACTIX_CHESSCOM_FIXTURE_PGN_PATH",
            DEFAULT_CHESSCOM_FIXTURE,
        )
    )
    use_fixture_when_no_token: bool = os.getenv("TACTIX_USE_FIXTURE", "1") == "1"
    chesscom_use_fixture_when_no_token: bool = (
        os.getenv("TACTIX_CHESSCOM_USE_FIXTURE", "1") == "1"
    )
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
    postgres_connect_timeout_s: int = int(
        os.getenv("TACTIX_POSTGRES_CONNECT_TIMEOUT", "5")
    )
    postgres_analysis_enabled: bool = (
        os.getenv("TACTIX_POSTGRES_ANALYSIS_ENABLED", "1") == "1"
    )
    postgres_pgns_enabled: bool = os.getenv("TACTIX_POSTGRES_PGNS_ENABLED", "1") == "1"
    run_context: str = os.getenv("TACTIX_RUN_CONTEXT", "app")

    def apply_stockfish_profile(self, profile: str | None = None) -> None:
        profile_value = (profile or "").strip().lower()
        if not profile_value:
            return
        if self.stockfish_depth is None:
            if profile_value == "bullet":
                self.stockfish_depth = DEFAULT_BULLET_STOCKFISH_DEPTH
            elif profile_value == "blitz":
                self.stockfish_depth = DEFAULT_BLITZ_STOCKFISH_DEPTH
            elif profile_value == "rapid":
                self.stockfish_depth = DEFAULT_RAPID_STOCKFISH_DEPTH
            elif profile_value == "classical":
                self.stockfish_depth = DEFAULT_CLASSICAL_STOCKFISH_DEPTH
            elif profile_value == "correspondence":
                self.stockfish_depth = DEFAULT_CORRESPONDENCE_STOCKFISH_DEPTH

    @property
    def data_dir(self) -> Path:
        return self.duckdb_path.parent

    def apply_source_defaults(self) -> None:
        self.source = (self.source or "lichess").lower()
        if self.source == "chesscom":
            self.user = self.chesscom_user
            if not self.chesscom_profile:
                inferred_profile = (
                    "correspondence"
                    if self.chesscom_time_class == "daily"
                    else self.chesscom_time_class
                )
                self.chesscom_profile = inferred_profile or "blitz"
            self.checkpoint_path = self.chesscom_checkpoint_path
            self.analysis_checkpoint_path = (
                self.data_dir / "analysis_checkpoint_chesscom.json"
            )
            self.fixture_pgn_path = self.chesscom_fixture_pgn_path
            self.use_fixture_when_no_token = self.chesscom_use_fixture_when_no_token
            self.apply_chesscom_profile()
        elif not self.user:
            self.user = self.lichess_user
        if self.source == "lichess":
            self.analysis_checkpoint_path = (
                self.data_dir / "analysis_checkpoint_lichess.json"
            )
            self.apply_lichess_profile()

    def apply_chesscom_profile(self, profile: str | None = None) -> None:
        profile_value = (profile or self.chesscom_profile or "").strip()
        if not profile_value:
            return
        if self.source != "chesscom":
            return
        self.chesscom_profile = profile_value
        time_class = "daily" if profile_value == "correspondence" else profile_value
        self.chesscom_time_class = time_class
        self.apply_stockfish_profile(profile_value)
        default_checkpoint = self.data_dir / "chesscom_since.txt"
        default_checkpoint_name = "chesscom_since.txt"
        profile_checkpoint = self.data_dir / f"chesscom_since_{profile_value}.txt"
        if (
            self.checkpoint_path == default_checkpoint
            or self.checkpoint_path.name == default_checkpoint_name
            or self.checkpoint_path.name.startswith("chesscom_since_")
        ):
            self.checkpoint_path = profile_checkpoint
        if (
            self.chesscom_checkpoint_path == DEFAULT_CHESSCOM_CHECKPOINT
            or self.chesscom_checkpoint_path == default_checkpoint
            or self.chesscom_checkpoint_path.name == default_checkpoint_name
            or self.chesscom_checkpoint_path.name.startswith("chesscom_since_")
        ):
            self.chesscom_checkpoint_path = self.checkpoint_path
        default_analysis = self.data_dir / "analysis_checkpoint_chesscom.json"
        default_analysis_name = "analysis_checkpoint_chesscom.json"
        profile_analysis = (
            self.data_dir / f"analysis_checkpoint_chesscom_{profile_value}.json"
        )
        if (
            self.analysis_checkpoint_path == DEFAULT_CHESSCOM_ANALYSIS_CHECKPOINT
            or self.analysis_checkpoint_path == default_analysis
            or self.analysis_checkpoint_path.name == default_analysis_name
            or self.analysis_checkpoint_path.name.startswith(
                "analysis_checkpoint_chesscom_"
            )
        ):
            self.analysis_checkpoint_path = profile_analysis
        repo_root = Path(__file__).resolve().parents[2]
        candidate = repo_root / f"tests/fixtures/chesscom_{profile_value}_sample.pgn"
        if candidate.exists():
            if (
                self.chesscom_fixture_pgn_path == DEFAULT_CHESSCOM_FIXTURE
                or self.chesscom_fixture_pgn_path.name.startswith("chesscom_")
                and self.chesscom_fixture_pgn_path.name.endswith("_sample.pgn")
            ):
                self.chesscom_fixture_pgn_path = candidate
            if (
                self.fixture_pgn_path == DEFAULT_CHESSCOM_FIXTURE
                or self.fixture_pgn_path.name.startswith("chesscom_")
                and self.fixture_pgn_path.name.endswith("_sample.pgn")
            ):
                self.fixture_pgn_path = candidate

    def apply_lichess_profile(self, profile: str | None = None) -> None:
        profile_value = (profile or self.lichess_profile or "").strip()
        if not profile_value:
            return
        self.lichess_profile = profile_value
        self.rapid_perf = profile_value
        self.apply_stockfish_profile(profile_value)
        if self.source != "lichess":
            return
        default_checkpoint = self.data_dir / "lichess_since.txt"
        if (
            self.checkpoint_path == DEFAULT_LICHESS_CHECKPOINT
            or self.checkpoint_path == default_checkpoint
        ):
            self.checkpoint_path = self.data_dir / f"lichess_since_{profile_value}.txt"
        default_analysis = self.data_dir / "analysis_checkpoint_lichess.json"
        if (
            self.analysis_checkpoint_path == DEFAULT_LICHESS_ANALYSIS_CHECKPOINT
            or self.analysis_checkpoint_path == default_analysis
        ):
            self.analysis_checkpoint_path = (
                self.data_dir / f"analysis_checkpoint_lichess_{profile_value}.json"
            )
        if self.fixture_pgn_path == DEFAULT_LICHESS_FIXTURE:
            repo_root = Path(__file__).resolve().parents[2]
            candidate = repo_root / f"tests/fixtures/lichess_{profile_value}_sample.pgn"
            if candidate.exists():
                self.fixture_pgn_path = candidate

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.chesscom_checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.metrics_version_file.parent.mkdir(parents=True, exist_ok=True)
        self.analysis_checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.lichess_token_cache_path.parent.mkdir(parents=True, exist_ok=True)


def get_settings(source: str | None = None, profile: str | None = None) -> Settings:
    settings = Settings()
    load_dotenv()
    lichess_username = os.getenv("LICHESS_USERNAME") or os.getenv("LICHESS_USER")
    if lichess_username:
        settings.lichess_user = lichess_username
        if not os.getenv("TACTIX_USER"):
            settings.user = lichess_username
    chesscom_username = os.getenv("CHESSCOM_USERNAME")
    if chesscom_username:
        settings.chesscom_user = chesscom_username
    if source:
        settings.source = source
    settings.apply_source_defaults()
    settings.apply_lichess_profile(profile)
    settings.apply_chesscom_profile(profile)
    settings.ensure_dirs()
    return settings
