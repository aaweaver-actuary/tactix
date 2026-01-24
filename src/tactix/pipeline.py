from __future__ import annotations

import hashlib
import json
import time

import chess.engine
from tactix.chesscom_client import (
    ChesscomFetchResult,
    fetch_incremental_games as fetch_chesscom_games,
    read_cursor as read_chesscom_cursor,
    write_cursor as write_chesscom_cursor,
)
from tactix.config import Settings, get_settings
from tactix.duckdb_store import (
    fetch_metrics,
    fetch_positions_for_games,
    fetch_recent_positions,
    fetch_recent_tactics,
    fetch_version,
    get_connection,
    init_schema,
    insert_positions,
    delete_game_rows,
    update_metrics_summary,
    upsert_raw_pgns,
    upsert_tactic_with_outcome,
    write_metrics_version,
)
from tactix.lichess_client import (
    fetch_incremental_games as fetch_lichess_games,
    read_checkpoint,
    write_checkpoint,
)
from tactix.logging_utils import get_logger
from tactix.pgn_utils import latest_timestamp
from tactix.position_extractor import extract_positions
from tactix.stockfish_runner import StockfishEngine
from tactix.tactics_analyzer import analyze_position

logger = get_logger(__name__)


def _analysis_signature(game_ids: list[str], positions_count: int, source: str) -> str:
    payload = {
        "game_ids": game_ids,
        "positions_count": positions_count,
        "source": source,
    }
    serialized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _read_analysis_checkpoint(checkpoint_path, signature: str) -> int:
    if not checkpoint_path.exists():
        return -1
    try:
        data = json.loads(checkpoint_path.read_text())
    except json.JSONDecodeError:
        return -1
    if data.get("signature") != signature:
        return -1
    return int(data.get("index", -1))


def _write_analysis_checkpoint(checkpoint_path, signature: str, index: int) -> None:
    payload = {"signature": signature, "index": index}
    checkpoint_path.write_text(json.dumps(payload))


def _clear_analysis_checkpoint(checkpoint_path) -> None:
    if checkpoint_path.exists():
        checkpoint_path.unlink()


def _analyse_with_retries(
    engine: StockfishEngine, position: dict[str, object], settings: Settings
) -> tuple[dict[str, object], dict[str, object]] | None:
    max_retries = max(settings.stockfish_max_retries, 0)
    backoff_seconds = max(settings.stockfish_retry_backoff_ms, 0) / 1000.0
    attempt = 0
    while True:
        try:
            return analyze_position(position, engine)
        except (
            chess.engine.EngineTerminatedError,
            chess.engine.EngineError,
            BrokenPipeError,
            OSError,
        ) as exc:
            attempt += 1
            if attempt > max_retries:
                raise
            logger.warning(
                "Stockfish error on attempt %s/%s: %s; restarting engine",
                attempt,
                max_retries,
                exc,
            )
            engine.restart()
            if backoff_seconds:
                time.sleep(backoff_seconds * (2 ** (attempt - 1)))


def run_daily_game_sync(
    settings: Settings | None = None, source: str | None = None
) -> dict[str, object]:
    settings = settings or get_settings(source=source)
    if source:
        settings.source = source
    settings.apply_source_defaults()
    settings.ensure_dirs()

    since_ms = 0
    cursor_value: str | None = None
    next_cursor: str | None = None
    chesscom_result: ChesscomFetchResult | None = None
    last_timestamp_value = 0

    if settings.source == "chesscom":
        cursor_value = read_chesscom_cursor(settings.checkpoint_path)
        if cursor_value:
            try:
                last_timestamp_value = int(cursor_value.split(":", 1)[0])
            except ValueError:
                last_timestamp_value = 0
        chesscom_result = fetch_chesscom_games(settings, cursor_value)
        games = chesscom_result.games
        next_cursor = chesscom_result.next_cursor or cursor_value
        last_timestamp_value = chesscom_result.last_timestamp_ms
    else:
        since_ms = read_checkpoint(settings.checkpoint_path)
        games = fetch_lichess_games(settings, since_ms)
        last_timestamp_value = since_ms

    conn = get_connection(settings.duckdb_path)
    init_schema(conn)

    if not games:
        logger.info(
            "No new games for source=%s at checkpoint=%s", settings.source, since_ms
        )
        update_metrics_summary(conn)
        metrics_version = write_metrics_version(conn)
        settings.metrics_version_file.write_text(str(metrics_version))
        return {
            "source": settings.source,
            "user": settings.user,
            "fetched_games": 0,
            "positions": 0,
            "tactics": 0,
            "metrics_version": metrics_version,
            "checkpoint_ms": since_ms if settings.source != "chesscom" else None,
            "cursor": next_cursor or cursor_value,
            "last_timestamp_ms": last_timestamp_value or since_ms,
            "since_ms": since_ms,
        }

    game_ids = [game["game_id"] for game in games]
    analysis_checkpoint_path = settings.analysis_checkpoint_path
    positions: list[dict[str, object]] = []
    resume_index = -1
    analysis_signature = ""

    if analysis_checkpoint_path.exists():
        existing_positions = fetch_positions_for_games(conn, game_ids)
        if existing_positions:
            analysis_signature = _analysis_signature(
                game_ids, len(existing_positions), settings.source
            )
            resume_index = _read_analysis_checkpoint(
                analysis_checkpoint_path, analysis_signature
            )
            if resume_index >= 0:
                logger.info(
                    "Resuming analysis at index=%s for source=%s",
                    resume_index,
                    settings.source,
                )
                positions = existing_positions
            else:
                _clear_analysis_checkpoint(analysis_checkpoint_path)
        else:
            _clear_analysis_checkpoint(analysis_checkpoint_path)

    if not positions:
        delete_game_rows(conn, game_ids)
        upsert_raw_pgns(conn, games)

        for game in games:
            positions.extend(
                extract_positions(
                    game["pgn"],
                    settings.user,
                    settings.source,
                    game_id=game["game_id"],
                )
            )

        position_ids = insert_positions(conn, positions)
        for pos, pos_id in zip(positions, position_ids, strict=False):
            pos["position_id"] = pos_id

        analysis_signature = _analysis_signature(
            game_ids, len(positions), settings.source
        )
    else:
        upsert_raw_pgns(conn, games)

    tactics_count = 0
    analysis_complete = False
    with StockfishEngine(settings) as engine:
        for idx, pos in enumerate(positions):
            if idx <= resume_index:
                continue
            result = _analyse_with_retries(engine, pos, settings)
            if result is None:
                _write_analysis_checkpoint(
                    analysis_checkpoint_path, analysis_signature, idx
                )
                continue
            tactic_row, outcome_row = result
            upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
            tactics_count += 1
            _write_analysis_checkpoint(
                analysis_checkpoint_path, analysis_signature, idx
            )
    analysis_complete = True
    if analysis_complete:
        _clear_analysis_checkpoint(analysis_checkpoint_path)
    update_metrics_summary(conn)
    metrics_version = write_metrics_version(conn)
    settings.metrics_version_file.write_text(str(metrics_version))

    checkpoint_value: int | None = None
    if settings.source == "chesscom":
        write_chesscom_cursor(settings.checkpoint_path, next_cursor)
        if chesscom_result:
            last_timestamp_value = chesscom_result.last_timestamp_ms
        elif games:
            last_timestamp_value = latest_timestamp(games)
    else:
        checkpoint_value = max(since_ms, latest_timestamp(games))
        write_checkpoint(settings.checkpoint_path, checkpoint_value)
        last_timestamp_value = checkpoint_value

    return {
        "source": settings.source,
        "user": settings.user,
        "fetched_games": len(games),
        "positions": len(positions),
        "tactics": tactics_count,
        "metrics_version": metrics_version,
        "checkpoint_ms": checkpoint_value,
        "cursor": next_cursor or cursor_value,
        "last_timestamp_ms": last_timestamp_value,
        "since_ms": since_ms,
    }


def run_refresh_metrics(
    settings: Settings | None = None, source: str | None = None
) -> dict[str, object]:
    settings = settings or get_settings(source=source)
    if source:
        settings.source = source
    settings.apply_source_defaults()
    settings.ensure_dirs()

    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    update_metrics_summary(conn)
    metrics_version = write_metrics_version(conn)
    settings.metrics_version_file.write_text(str(metrics_version))

    return {
        "source": settings.source,
        "user": settings.user,
        "metrics_version": metrics_version,
        "metrics_rows": len(fetch_metrics(conn, source=settings.source)),
    }


def get_dashboard_payload(
    settings: Settings | None = None, source: str | None = None
) -> dict[str, object]:
    settings = settings or get_settings(source=source)
    if source:
        settings.source = source
    settings.apply_source_defaults()
    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    active_source = source or settings.source
    return {
        "source": active_source,
        "user": settings.user,
        "metrics": fetch_metrics(conn, source=active_source),
        "positions": fetch_recent_positions(conn, source=active_source),
        "tactics": fetch_recent_tactics(conn, source=active_source),
        "metrics_version": fetch_version(conn),
    }
