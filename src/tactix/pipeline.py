from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from collections.abc import Callable

import chess.engine
from tactix.chesscom_client import (
    ChesscomFetchResult,
    fetch_incremental_games as fetch_chesscom_games,
    read_cursor as read_chesscom_cursor,
    write_cursor as write_chesscom_cursor,
)
from tactix.config import Settings, get_settings
from tactix.duckdb_store import (
    fetch_latest_pgn_hashes,
    fetch_metrics,
    fetch_positions_for_games,
    fetch_position_counts,
    fetch_recent_positions,
    fetch_recent_tactics,
    get_schema_version,
    fetch_version,
    get_connection,
    hash_pgn,
    init_schema,
    insert_positions,
    delete_game_rows,
    migrate_schema,
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


ProgressCallback = Callable[[dict[str, object]], None]


def _emit_progress(
    progress: ProgressCallback | None, step: str, **fields: object
) -> None:
    if progress is None:
        return
    payload: dict[str, object] = {"step": step, "timestamp": time.time()}
    payload.update(fields)
    progress(payload)


def _dedupe_games(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[tuple[str, str, int]] = set()
    deduped: list[dict[str, object]] = []
    for game in rows:
        game_id = str(game.get("game_id", ""))
        source = str(game.get("source", ""))
        last_ts = int(game.get("last_timestamp_ms", 0) or 0)
        key = (game_id, source, last_ts)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(game)
    return deduped


def _filter_games_by_window(
    rows: list[dict[str, object]],
    start_ms: int | None,
    end_ms: int | None,
) -> list[dict[str, object]]:
    if start_ms is None and end_ms is None:
        return rows
    filtered: list[dict[str, object]] = []
    for game in rows:
        last_ts = int(game.get("last_timestamp_ms", 0) or 0)
        if start_ms is not None and last_ts < start_ms:
            continue
        if end_ms is not None and last_ts >= end_ms:
            continue
        filtered.append(game)
    return filtered


def _filter_backfill_games(
    conn,
    rows: list[dict[str, object]],
    source: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    if not rows:
        return [], []
    game_ids = [str(row.get("game_id", "")) for row in rows]
    latest_hashes = fetch_latest_pgn_hashes(conn, game_ids, source)
    position_counts = fetch_position_counts(conn, game_ids, source)
    to_process: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    for game in rows:
        game_id = str(game.get("game_id", ""))
        pgn_text = str(game.get("pgn", ""))
        current_hash = hash_pgn(pgn_text)
        existing_hash = latest_hashes.get(game_id)
        if existing_hash == current_hash and position_counts.get(game_id, 0) > 0:
            skipped.append(game)
            continue
        to_process.append(game)
    return to_process, skipped


def run_migrations(
    settings: Settings | None = None,
    source: str | None = None,
    progress: ProgressCallback | None = None,
) -> dict[str, object]:
    settings = settings or get_settings(source=source)
    if source:
        settings.source = source
    settings.apply_source_defaults()
    settings.ensure_dirs()

    _emit_progress(
        progress,
        "migrations_start",
        source=settings.source,
        message="Starting DuckDB schema migrations",
    )

    conn = get_connection(settings.duckdb_path)
    migrate_schema(conn)
    schema_version = get_schema_version(conn)

    _emit_progress(
        progress,
        "migrations_complete",
        source=settings.source,
        schema_version=schema_version,
    )

    return {
        "source": settings.source,
        "schema_version": schema_version,
    }


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
    settings: Settings | None = None,
    source: str | None = None,
    progress: ProgressCallback | None = None,
    window_start_ms: int | None = None,
    window_end_ms: int | None = None,
) -> dict[str, object]:
    settings = settings or get_settings(source=source)
    if source:
        settings.source = source
    settings.apply_source_defaults()
    settings.ensure_dirs()

    backfill_mode = window_start_ms is not None or window_end_ms is not None

    _emit_progress(
        progress,
        "start",
        source=settings.source,
        message="Starting pipeline run",
    )

    since_ms = 0
    cursor_value: str | None = None
    next_cursor: str | None = None
    chesscom_result: ChesscomFetchResult | None = None
    last_timestamp_value = 0
    checkpoint_before: int | None = None
    cursor_before: str | None = None

    if settings.source == "chesscom":
        cursor_before = read_chesscom_cursor(settings.checkpoint_path)
        cursor_value = None if backfill_mode else cursor_before
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
        checkpoint_before = read_checkpoint(settings.checkpoint_path)
        since_ms = window_start_ms if backfill_mode else checkpoint_before
        if since_ms is None:
            since_ms = 0
        games = fetch_lichess_games(settings, since_ms)
        last_timestamp_value = since_ms

    games = _dedupe_games(games)
    games = _filter_games_by_window(games, window_start_ms, window_end_ms)
    if games:
        last_timestamp_value = latest_timestamp(games) or last_timestamp_value

    _emit_progress(
        progress,
        "fetch_games",
        source=settings.source,
        fetched_games=len(games),
        since_ms=since_ms,
        cursor=next_cursor or cursor_value,
        backfill=backfill_mode,
        backfill_start_ms=window_start_ms,
        backfill_end_ms=window_end_ms,
    )

    conn = get_connection(settings.duckdb_path)
    init_schema(conn)

    if not games:
        logger.info(
            "No new games for source=%s at checkpoint=%s", settings.source, since_ms
        )
        _emit_progress(
            progress,
            "no_games",
            source=settings.source,
            message="No new games to process",
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
            "checkpoint_ms": None
            if backfill_mode or settings.source == "chesscom"
            else since_ms,
            "cursor": cursor_before if backfill_mode else (next_cursor or cursor_value),
            "last_timestamp_ms": last_timestamp_value or since_ms,
            "since_ms": since_ms,
        }

    games_to_process = games
    skipped_games: list[dict[str, object]] = []
    if backfill_mode:
        games_to_process, skipped_games = _filter_backfill_games(
            conn, games, settings.source
        )
        if skipped_games:
            logger.info(
                "Skipping %s historical games already processed for source=%s",
                len(skipped_games),
                settings.source,
            )
    if not games_to_process:
        logger.info(
            "No new games to process after backfill dedupe for source=%s",
            settings.source,
        )
        update_metrics_summary(conn)
        metrics_version = write_metrics_version(conn)
        settings.metrics_version_file.write_text(str(metrics_version))
        if not backfill_mode:
            if settings.source == "chesscom":
                write_chesscom_cursor(settings.checkpoint_path, next_cursor)
            else:
                checkpoint_value = max(since_ms, last_timestamp_value)
                write_checkpoint(settings.checkpoint_path, checkpoint_value)
                last_timestamp_value = checkpoint_value
        return {
            "source": settings.source,
            "user": settings.user,
            "fetched_games": len(games),
            "positions": 0,
            "tactics": 0,
            "metrics_version": metrics_version,
            "checkpoint_ms": None
            if backfill_mode
            else max(since_ms, last_timestamp_value),
            "cursor": cursor_before if backfill_mode else (next_cursor or cursor_value),
            "last_timestamp_ms": last_timestamp_value,
            "since_ms": since_ms,
        }

    game_ids = [game["game_id"] for game in games_to_process]
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
        _emit_progress(
            progress,
            "raw_pgns",
            source=settings.source,
            message="Persisting raw PGNs",
        )
        delete_game_rows(conn, game_ids)
        upsert_raw_pgns(conn, games_to_process)

        _emit_progress(
            progress,
            "extract_positions",
            source=settings.source,
            message="Extracting positions",
        )

        for game in games_to_process:
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
        upsert_raw_pgns(conn, games_to_process)

    _emit_progress(
        progress,
        "positions_ready",
        source=settings.source,
        positions=len(positions),
    )

    tactics_count = 0
    analysis_complete = False
    total_positions = len(positions)
    progress_every = max(1, total_positions // 20) if total_positions else 1
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
            if progress and (
                idx == total_positions - 1 or (idx + 1) % progress_every == 0
            ):
                _emit_progress(
                    progress,
                    "analyze_positions",
                    source=settings.source,
                    analyzed=idx + 1,
                    total=total_positions,
                )
    analysis_complete = True
    if analysis_complete:
        _clear_analysis_checkpoint(analysis_checkpoint_path)
    update_metrics_summary(conn)
    metrics_version = write_metrics_version(conn)
    settings.metrics_version_file.write_text(str(metrics_version))

    _emit_progress(
        progress,
        "metrics_refreshed",
        source=settings.source,
        metrics_version=metrics_version,
        message="Metrics refreshed",
    )

    checkpoint_value: int | None = None
    if not backfill_mode:
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
        "cursor": cursor_before if backfill_mode else (next_cursor or cursor_value),
        "last_timestamp_ms": last_timestamp_value,
        "since_ms": since_ms,
    }


def run_refresh_metrics(
    settings: Settings | None = None,
    source: str | None = None,
    progress: ProgressCallback | None = None,
) -> dict[str, object]:
    settings = settings or get_settings(source=source)
    if source:
        settings.source = source
    settings.apply_source_defaults()
    settings.ensure_dirs()

    _emit_progress(
        progress,
        "start",
        source=settings.source,
        message="Refreshing metrics",
    )

    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    update_metrics_summary(conn)
    metrics_version = write_metrics_version(conn)
    settings.metrics_version_file.write_text(str(metrics_version))

    _emit_progress(
        progress,
        "metrics_refreshed",
        source=settings.source,
        metrics_version=metrics_version,
        message="Metrics refreshed",
    )

    return {
        "source": settings.source,
        "user": settings.user,
        "metrics_version": metrics_version,
        "metrics_rows": len(fetch_metrics(conn, source=settings.source)),
    }


def get_dashboard_payload(
    settings: Settings | None = None,
    source: str | None = None,
    motif: str | None = None,
    rating_bucket: str | None = None,
    time_control: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
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
        "metrics": fetch_metrics(
            conn,
            source=active_source,
            motif=motif,
            rating_bucket=rating_bucket,
            time_control=time_control,
            start_date=start_date,
            end_date=end_date,
        ),
        "positions": fetch_recent_positions(
            conn,
            source=active_source,
            rating_bucket=rating_bucket,
            time_control=time_control,
            start_date=start_date,
            end_date=end_date,
        ),
        "tactics": fetch_recent_tactics(
            conn,
            source=active_source,
            motif=motif,
            rating_bucket=rating_bucket,
            time_control=time_control,
            start_date=start_date,
            end_date=end_date,
        ),
        "metrics_version": fetch_version(conn),
    }
