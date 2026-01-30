from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from tactix.refresh_dashboard_cache_async__api_cache import _refresh_dashboard_cache_async


@asynccontextmanager
async def lifespan(_: FastAPI):
    _refresh_dashboard_cache_async([None, "lichess", "chesscom"])
    yield
