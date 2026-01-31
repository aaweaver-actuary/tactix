from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class LichessSettings:
    """Lichess-specific configuration."""

    user: str = os.getenv("LICHESS_USERNAME", os.getenv("LICHESS_USER", "lichess"))
    token: str | None = os.getenv("LICHESS_TOKEN")
    oauth_client_id: str | None = os.getenv("LICHESS_OAUTH_CLIENT_ID")
    oauth_client_secret: str | None = os.getenv("LICHESS_OAUTH_CLIENT_SECRET")
    oauth_refresh_token: str | None = os.getenv("LICHESS_OAUTH_REFRESH_TOKEN")
    oauth_token_url: str = os.getenv("LICHESS_OAUTH_TOKEN_URL", "https://lichess.org/api/token")

    profile: str = os.getenv("TACTIX_LICHESS_PROFILE", "")
    data_dir: Path = Path(os.getenv("LICHESS_DATA_DIR"))

    def __post_init__(self) -> None:
        if not self.data_dir.exists():
            self.data_dir.mkdir(parents=True, exist_ok=True)
        self.token_cache_path: Path = Path(
            os.getenv("LICHESS_TOKEN_CACHE_PATH", str(self.data_dir / "lichess_token.json"))
        )
