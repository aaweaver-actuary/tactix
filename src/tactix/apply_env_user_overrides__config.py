from __future__ import annotations

import os

from tactix.define_settings__config import Settings


def _apply_env_user_overrides(settings: Settings) -> None:
    lichess_username = os.getenv("LICHESS_USERNAME") or os.getenv("LICHESS_USER")
    if lichess_username:
        settings.lichess_user = lichess_username
        if not os.getenv("TACTIX_USER"):
            settings.user = lichess_username
    chesscom_username = os.getenv("CHESSCOM_USERNAME")
    if chesscom_username:
        settings.chesscom_user = chesscom_username
