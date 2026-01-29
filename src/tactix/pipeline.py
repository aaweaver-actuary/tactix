from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from collections.abc import Callable, Mapping
from typing import TypedDict, cast

import chess.engine
from tactix.base_db_store import BaseDbStore, BaseDbStoreContext
from tactix.base_chess_client import BaseChessClient
from tactix.chesscom_client import (
    ChesscomClient,
    ChesscomClientContext,
    ChesscomFetchRequest,
    ChesscomFetchResult,
    read_cursor as read_chesscom_cursor,
    write_cursor as write_chesscom_cursor,
)
from tactix.config import Settings, get_settings
from tactix.duckdb_store import (
    DuckDbStore,
    fetch_latest_pgn_hashes,
    fetch_latest_raw_pgns,
    fetch_metrics,
    fetch_unanalyzed_positions,
    fetch_positions_for_games,
    fetch_position_counts,
    fetch_recent_tactics,
    get_schema_version,
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
    LichessClient,
    LichessClientContext,
    LichessFetchRequest,
    read_checkpoint,
    write_checkpoint,
)
from tactix.logging_utils import get_logger
from tactix.pgn_utils import (
    extract_game_id,
    extract_last_timestamp_ms,
    latest_timestamp,
    split_pgn_chunks,
)
from tactix.position_extractor import extract_positions
from tactix.postgres_store import (
    init_analysis_schema,
    init_pgn_schema,
    postgres_analysis_enabled,
    postgres_pgns_enabled,
    postgres_connection,
    record_ops_event,
    upsert_analysis_tactic_with_outcome,
    upsert_postgres_raw_pgns,
)
from tactix.stockfish_runner import StockfishEngine
from tactix.tactics_analyzer import analyze_position

logger = get_logger(__name__)


class GameRow(TypedDict):
    game_id: str
    user: str
    source: str
    fetched_at: datetime
    pgn: str
    last_timestamp_ms: int


ProgressCallback = Callable[[dict[str, object]], None]


def _coerce_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _coerce_str(value: object) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return str(value)


def _coerce_pgn(value: object) -> str:
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    return _coerce_str(value)


def _normalize_game_row(row: Mapping[str, object], settings: Settings) -> GameRow:
    fetched_at = row.get("fetched_at")
    if not isinstance(fetched_at, datetime):
        fetched_at = datetime.now()
    return {
        "game_id": _coerce_str(row.get("game_id")),
        "user": _coerce_str(row.get("user")) or settings.user,
        "source": _coerce_str(row.get("source")) or settings.source,
        "fetched_at": fetched_at,
        "pgn": _coerce_pgn(row.get("pgn")),
        "last_timestamp_ms": _coerce_int(row.get("last_timestamp_ms")),
    }


def _expand_pgn_rows(rows: list[GameRow], settings: Settings) -> list[GameRow]:
    expanded: list[GameRow] = []
    for row in rows:
        pgn_text = row.get("pgn", "")
        chunks = split_pgn_chunks(pgn_text)
        if len(chunks) <= 1:
            expanded.append(row)
            continue
        for chunk in chunks:
            expanded.append(
                {
                    "game_id": extract_game_id(chunk),
                    "user": row.get("user") or settings.user,
                    "source": row.get("source") or settings.source,
                    "fetched_at": row.get("fetched_at"),
                    "pgn": chunk,
                    "last_timestamp_ms": extract_last_timestamp_ms(chunk),
                }
            )
    return expanded


def _resolve_side_to_move_filter(settings: Settings) -> str | None:
    source = (settings.source or "").strip().lower()
    if source == "lichess":
        profile = (
            (settings.lichess_profile or settings.rapid_perf or "").strip().lower()
        )
        if profile in {"bullet", "blitz", "rapid", "classical", "correspondence"}:
            return "black"
        return None
    if source == "chesscom":
        profile = (
            (settings.chesscom_profile or settings.chesscom_time_class or "")
            .strip()
            .lower()
        )
        if profile in {"bullet", "blitz", "rapid", "classical"}:
            return "black"
        if profile in {"correspondence", "daily"}:
            return "black"
    return None


def _emit_progress(
    progress: ProgressCallback | None, step: str, **fields: object
) -> None:
    if progress is None:
        return
    payload: dict[str, object] = {"step": step, "timestamp": time.time()}
    payload.update(fields)
    progress(payload)


def _dedupe_games(rows: list[GameRow]) -> list[GameRow]:
    seen: set[tuple[str, str, int]] = set()
    deduped: list[GameRow] = []
    for game in rows:
        game_id = game["game_id"]
        source = game["source"]
        last_ts = game["last_timestamp_ms"]
        key = (game_id, source, last_ts)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(game)
    return deduped


def _filter_games_by_window(
    rows: list[GameRow],
    start_ms: int | None,
    end_ms: int | None,
) -> list[GameRow]:
    if start_ms is None and end_ms is None:
        return rows
    filtered: list[GameRow] = []
    for game in rows:
        last_ts = game["last_timestamp_ms"]
        if start_ms is not None and last_ts < start_ms:
            continue
        if end_ms is not None and last_ts >= end_ms:
            continue
        filtered.append(game)
    return filtered


def _filter_backfill_games(
    conn,
    rows: list[GameRow],
    source: str,
) -> tuple[list[GameRow], list[GameRow]]:
    if not rows:
        return [], []
    game_ids = [row["game_id"] for row in rows]
    latest_hashes = fetch_latest_pgn_hashes(conn, game_ids, source)
    position_counts = fetch_position_counts(conn, game_ids, source)
    to_process: list[GameRow] = []
    skipped: list[GameRow] = []
    for game in rows:
        game_id = game["game_id"]
        pgn_text = game["pgn"]
        current_hash = hash_pgn(pgn_text)
        existing_hash = latest_hashes.get(game_id)
        if existing_hash == current_hash and position_counts.get(game_id, 0) > 0:
            skipped.append(game)
            continue
        to_process.append(game)
    return to_process, skipped


def _compute_pgn_hashes(rows: list[GameRow], source: str) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for row in rows:
        game_id = row["game_id"]
        if game_id in hashes:
            raise ValueError(
                f"Duplicate game_id in raw PGN batch for source={source}: {game_id}"
            )
        hashes[game_id] = hash_pgn(row["pgn"])
    return hashes


def _validate_raw_pgn_hashes(
    conn,
    rows: list[GameRow],
    source: str,
) -> dict[str, int]:
    if not rows:
        return {"computed": 0, "matched": 0}
    computed = _compute_pgn_hashes(rows, source)
    stored = fetch_latest_pgn_hashes(conn, list(computed.keys()), source)
    matched = sum(
        1 for game_id, pgn_hash in computed.items() if stored.get(game_id) == pgn_hash
    )
    if matched != len(computed):
        missing = [
            game_id
            for game_id, pgn_hash in computed.items()
            if stored.get(game_id) != pgn_hash
        ]
        raise ValueError(
            "Raw PGN hash mismatch for source=%s expected=%s matched=%s missing=%s"
            % (source, len(computed), matched, ", ".join(sorted(missing)))
        )
    return {"computed": len(computed), "matched": matched}


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


def convert_raw_pgns_to_positions(
    settings: Settings | None = None,
    source: str | None = None,
    profile: str | None = None,
    limit: int | None = None,
) -> dict[str, object]:
    settings = settings or get_settings(source=source, profile=profile)
    if source:
        settings.source = source
    settings.apply_source_defaults()
    settings.apply_lichess_profile(profile)
    settings.apply_chesscom_profile(profile)
    settings.ensure_dirs()

    conn = get_connection(settings.duckdb_path)
    init_schema(conn)

    raw_pgns = fetch_latest_raw_pgns(conn, settings.source, limit)
    if not raw_pgns:
        return {
            "source": settings.source,
            "games": 0,
            "inserted_games": 0,
            "positions": 0,
        }

    game_ids = [str(row.get("game_id", "")) for row in raw_pgns if row.get("game_id")]
    position_counts = fetch_position_counts(conn, game_ids, settings.source)
    to_process = [
        row for row in raw_pgns if position_counts.get(str(row.get("game_id")), 0) == 0
    ]

    positions: list[dict[str, object]] = []
    side_to_move_filter = _resolve_side_to_move_filter(settings)
    for row in to_process:
        positions.extend(
            extract_positions(
                str(row.get("pgn", "")),
                str(row.get("user") or settings.user),
                str(row.get("source") or settings.source),
                game_id=str(row.get("game_id", "")),
                side_to_move_filter=side_to_move_filter,
            )
        )

    position_ids = insert_positions(conn, positions)
    for pos, pos_id in zip(positions, position_ids, strict=False):
        pos["position_id"] = pos_id

    return {
        "source": settings.source,
        "games": len(raw_pgns),
        "inserted_games": len(to_process),
        "positions": len(positions),
    }


def _extract_positions_for_new_games(
    conn, settings: Settings, raw_pgns: list[dict[str, object]]
) -> tuple[list[dict[str, object]], list[str]]:
    game_ids = [str(row.get("game_id", "")) for row in raw_pgns if row.get("game_id")]
    if not game_ids:
        return [], []
    position_counts = fetch_position_counts(conn, game_ids, settings.source)
    to_process = [
        row for row in raw_pgns if position_counts.get(str(row.get("game_id")), 0) == 0
    ]
    if not to_process:
        return [], []
    positions: list[dict[str, object]] = []
    side_to_move_filter = _resolve_side_to_move_filter(settings)
    for row in to_process:
        positions.extend(
            extract_positions(
                str(row.get("pgn", "")),
                str(row.get("user") or settings.user),
                str(row.get("source") or settings.source),
                game_id=str(row.get("game_id", "")),
                side_to_move_filter=side_to_move_filter,
            )
        )
    position_ids = insert_positions(conn, positions)
    for pos, pos_id in zip(positions, position_ids, strict=False):
        pos["position_id"] = pos_id
    return positions, [str(row.get("game_id", "")) for row in to_process]


def _analyze_positions(
    conn, settings: Settings, positions: list[dict[str, object]]
) -> tuple[int, int]:
    if not positions:
        return 0, 0
    positions_analyzed = 0
    tactics_detected = 0
    postgres_written = 0
    postgres_synced = 0
    analysis_pg_enabled = postgres_analysis_enabled(settings)
    with postgres_connection(settings) as pg_conn:
        if pg_conn is not None and analysis_pg_enabled:
            init_analysis_schema(pg_conn)
        with StockfishEngine(settings) as engine:
            for pos in positions:
                positions_analyzed += 1
                result = _analyse_with_retries(engine, pos, settings)
                if result is None:
                    continue
                tactic_row, outcome_row = result
                upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
                if pg_conn is not None and analysis_pg_enabled:
                    try:
                        upsert_analysis_tactic_with_outcome(
                            pg_conn,
                            tactic_row,
                            outcome_row,
                        )
                        postgres_written += 1
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Postgres analysis upsert failed: %s", exc)
                tactics_detected += 1
        if pg_conn is not None and analysis_pg_enabled and postgres_written == 0:
            postgres_synced = _sync_postgres_analysis_results(conn, pg_conn, settings)
            postgres_written += postgres_synced
    record_ops_event(
        settings,
        component="analysis",
        event_type="analysis_complete",
        source=settings.source,
        profile=settings.lichess_profile or settings.chesscom_profile,
        metadata={
            "positions_analyzed": positions_analyzed,
            "tactics_detected": tactics_detected,
            "postgres_tactics_written": postgres_written,
            "postgres_tactics_synced": postgres_synced,
        },
    )
    return positions_analyzed, tactics_detected


def _sync_postgres_analysis_results(
    conn,
    pg_conn,
    settings: Settings,
    limit: int = 50,
) -> int:
    if pg_conn is None:
        return 0
    synced = 0
    recent = fetch_recent_tactics(conn, limit=limit, source=settings.source)
    for row in recent:
        tactic_row = {
            "game_id": row.get("game_id"),
            "position_id": row.get("position_id"),
            "motif": row.get("motif", "unknown"),
            "severity": row.get("severity", 0.0),
            "best_uci": row.get("best_uci", ""),
            "best_san": row.get("best_san"),
            "explanation": row.get("explanation"),
            "eval_cp": row.get("eval_cp", 0),
        }
        outcome_row = {
            "result": row.get("result", "unclear"),
            "user_uci": row.get("user_uci", ""),
            "eval_delta": row.get("eval_delta", 0),
        }
        try:
            upsert_analysis_tactic_with_outcome(
                pg_conn,
                tactic_row,
                outcome_row,
            )
            synced += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Postgres analysis sync failed: %s", exc)
    return synced


def run_monitor_new_positions(
    settings: Settings | None = None,
    source: str | None = None,
    profile: str | None = None,
    limit: int | None = None,
) -> dict[str, object]:
    settings = settings or get_settings(source=source, profile=profile)
    if source:
        settings.source = source
    settings.apply_source_defaults()
    settings.apply_lichess_profile(profile)
    settings.apply_chesscom_profile(profile)
    settings.ensure_dirs()

    conn = get_connection(settings.duckdb_path)
    init_schema(conn)

    raw_pgns = fetch_latest_raw_pgns(conn, settings.source, limit)
    positions_extracted = 0
    new_game_ids: list[str] = []
    if raw_pgns:
        extracted_positions, new_game_ids = _extract_positions_for_new_games(
            conn, settings, raw_pgns
        )
        positions_extracted = len(extracted_positions)

    positions_to_analyze: list[dict[str, object]] = []
    if new_game_ids:
        positions_to_analyze = fetch_unanalyzed_positions(
            conn, game_ids=new_game_ids, source=settings.source
        )

    positions_analyzed, tactics_detected = _analyze_positions(
        conn, settings, positions_to_analyze
    )

    update_metrics_summary(conn)
    metrics_version = write_metrics_version(conn)
    settings.metrics_version_file.write_text(str(metrics_version))

    logger.info(
        "Monitor run complete: source=%s new_games=%s positions_extracted=%s positions_analyzed=%s tactics_detected=%s metrics_version=%s",
        settings.source,
        len(new_game_ids),
        positions_extracted,
        positions_analyzed,
        tactics_detected,
        metrics_version,
    )

    record_ops_event(
        settings,
        component=settings.run_context,
        event_type="monitor_new_positions_complete",
        source=settings.source,
        profile=profile,
        metadata={
            "new_games": len(new_game_ids),
            "positions_extracted": positions_extracted,
            "positions_analyzed": positions_analyzed,
            "tactics_detected": tactics_detected,
            "metrics_version": metrics_version,
        },
    )

    return {
        "source": settings.source,
        "user": settings.user,
        "raw_pgns_checked": len(raw_pgns),
        "new_games": len(new_game_ids),
        "positions_extracted": positions_extracted,
        "positions_analyzed": positions_analyzed,
        "tactics_detected": tactics_detected,
        "metrics_version": metrics_version,
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
            return analyze_position(position, engine, settings=settings)
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
    profile: str | None = None,
    client: BaseChessClient | None = None,
) -> dict[str, object]:
    settings = settings or get_settings(source=source, profile=profile)
    if source:
        settings.source = source
    settings.apply_source_defaults()
    settings.apply_lichess_profile(profile)
    settings.apply_chesscom_profile(profile)
    settings.ensure_dirs()

    if client is None:
        if settings.source == "chesscom":
            client = ChesscomClient(
                ChesscomClientContext(settings=settings, logger=logger)
            )
        else:
            client = LichessClient(
                LichessClientContext(settings=settings, logger=logger)
            )
    assert client is not None

    backfill_mode = window_start_ms is not None or window_end_ms is not None

    _emit_progress(
        progress,
        "start",
        source=settings.source,
        message="Starting pipeline run",
    )
    record_ops_event(
        settings,
        component=settings.run_context,
        event_type="daily_game_sync_start",
        source=settings.source,
        profile=profile,
        metadata={
            "backfill": backfill_mode,
            "window_start_ms": window_start_ms,
            "window_end_ms": window_end_ms,
        },
    )

    since_ms = 0
    cursor_value: str | None = None
    next_cursor: str | None = None
    chesscom_result: ChesscomFetchResult | None = None
    last_timestamp_value = 0
    checkpoint_before: int | None = None
    cursor_before: str | None = None

    raw_games: list[Mapping[str, object]]
    if settings.source == "chesscom":
        cursor_before = read_chesscom_cursor(settings.checkpoint_path)
        cursor_value = None if backfill_mode else cursor_before
        if cursor_value:
            try:
                last_timestamp_value = int(cursor_value.split(":", 1)[0])
            except ValueError:
                last_timestamp_value = 0
        chesscom_result = cast(
            ChesscomFetchResult,
            client.fetch_incremental_games(
                ChesscomFetchRequest(cursor=cursor_value, full_history=backfill_mode)
            ),
        )
        raw_games = [cast(Mapping[str, object], row) for row in chesscom_result.games]
        next_cursor = chesscom_result.next_cursor or cursor_value
        last_timestamp_value = chesscom_result.last_timestamp_ms
    else:
        checkpoint_before = read_checkpoint(settings.checkpoint_path)
        since_ms = window_start_ms if backfill_mode else checkpoint_before
        if since_ms is None:
            since_ms = 0
        until_ms = window_end_ms if backfill_mode else None
        raw_games = [
            cast(Mapping[str, object], row)
            for row in client.fetch_incremental_games(
                LichessFetchRequest(since_ms=since_ms, until_ms=until_ms)
            ).games
        ]
        last_timestamp_value = since_ms

    games = [_normalize_game_row(game, settings) for game in raw_games]
    games = _expand_pgn_rows(games, settings)

    games = _dedupe_games(games)
    pre_window_count = len(games)
    games = _filter_games_by_window(games, window_start_ms, window_end_ms)
    window_filtered = pre_window_count - len(games)
    if backfill_mode and window_filtered:
        logger.info(
            "Filtered %s games outside backfill window for source=%s",
            window_filtered,
            settings.source,
        )
        _emit_progress(
            progress,
            "backfill_window_filtered",
            source=settings.source,
            filtered=window_filtered,
            backfill_start_ms=window_start_ms,
            backfill_end_ms=window_end_ms,
        )
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
            "raw_pgns_inserted": 0,
            "raw_pgns_hashed": 0,
            "raw_pgns_matched": 0,
            "positions": 0,
            "tactics": 0,
            "metrics_version": metrics_version,
            "checkpoint_ms": None
            if backfill_mode or settings.source == "chesscom"
            else since_ms,
            "cursor": cursor_before if backfill_mode else (next_cursor or cursor_value),
            "last_timestamp_ms": last_timestamp_value or since_ms,
            "since_ms": since_ms,
            "window_filtered": window_filtered,
        }

    games_to_process = games
    skipped_games: list[GameRow] = []
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
            "raw_pgns_inserted": 0,
            "raw_pgns_hashed": 0,
            "raw_pgns_matched": 0,
            "postgres_raw_pgns_inserted": 0,
            "positions": 0,
            "tactics": 0,
            "metrics_version": metrics_version,
            "checkpoint_ms": None
            if backfill_mode
            else max(since_ms, last_timestamp_value),
            "cursor": cursor_before if backfill_mode else (next_cursor or cursor_value),
            "last_timestamp_ms": last_timestamp_value,
            "since_ms": since_ms,
            "window_filtered": window_filtered,
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

    raw_pgns_inserted = 0
    raw_pgns_hashed = 0
    raw_pgns_matched = 0
    postgres_raw_pgns_inserted = 0
    postgres_pgns_active = postgres_pgns_enabled(settings)
    if not positions:
        _emit_progress(
            progress,
            "raw_pgns",
            source=settings.source,
            message="Persisting raw PGNs",
        )
        delete_game_rows(conn, game_ids)
        raw_pgns_inserted = upsert_raw_pgns(conn, games_to_process)
        hash_metrics = _validate_raw_pgn_hashes(conn, games_to_process, settings.source)
        raw_pgns_hashed = hash_metrics["computed"]
        raw_pgns_matched = hash_metrics["matched"]
        _emit_progress(
            progress,
            "raw_pgns_persisted",
            source=settings.source,
            inserted=raw_pgns_inserted,
            total=len(games_to_process),
        )
        _emit_progress(
            progress,
            "raw_pgns_hashed",
            source=settings.source,
            computed=raw_pgns_hashed,
            matched=raw_pgns_matched,
        )
        record_ops_event(
            settings,
            component="ingestion",
            event_type="raw_pgns_persisted",
            source=settings.source,
            profile=profile,
            metadata={
                "inserted": raw_pgns_inserted,
                "computed": raw_pgns_hashed,
                "matched": raw_pgns_matched,
                "total": len(games_to_process),
            },
        )
        if postgres_pgns_active:
            with postgres_connection(settings) as pg_conn:
                if pg_conn is None:
                    logger.warning(
                        "Postgres raw PGN mirror enabled but connection unavailable"
                    )
                else:
                    init_pgn_schema(pg_conn)
                    try:
                        postgres_raw_pgns_inserted = upsert_postgres_raw_pgns(
                            pg_conn,
                            cast(list[Mapping[str, object]], games_to_process),
                        )
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Postgres raw PGN upsert failed: %s", exc)
            _emit_progress(
                progress,
                "postgres_raw_pgns_persisted",
                source=settings.source,
                inserted=postgres_raw_pgns_inserted,
                total=len(games_to_process),
            )
            record_ops_event(
                settings,
                component="ingestion",
                event_type="postgres_raw_pgns_persisted",
                source=settings.source,
                profile=profile,
                metadata={
                    "inserted": postgres_raw_pgns_inserted,
                    "total": len(games_to_process),
                },
            )

        _emit_progress(
            progress,
            "extract_positions",
            source=settings.source,
            message="Extracting positions",
        )

        side_to_move_filter = _resolve_side_to_move_filter(settings)

        for game in games_to_process:
            positions.extend(
                extract_positions(
                    game["pgn"],
                    settings.user,
                    settings.source,
                    game_id=game["game_id"],
                    side_to_move_filter=side_to_move_filter,
                )
            )

        position_ids = insert_positions(conn, positions)
        for pos, pos_id in zip(positions, position_ids, strict=False):
            pos["position_id"] = pos_id

        analysis_signature = _analysis_signature(
            game_ids, len(positions), settings.source
        )
    else:
        raw_pgns_inserted = upsert_raw_pgns(conn, games_to_process)
        hash_metrics = _validate_raw_pgn_hashes(conn, games_to_process, settings.source)
        raw_pgns_hashed = hash_metrics["computed"]
        raw_pgns_matched = hash_metrics["matched"]
        _emit_progress(
            progress,
            "raw_pgns_persisted",
            source=settings.source,
            inserted=raw_pgns_inserted,
            total=len(games_to_process),
        )
        _emit_progress(
            progress,
            "raw_pgns_hashed",
            source=settings.source,
            computed=raw_pgns_hashed,
            matched=raw_pgns_matched,
        )
        record_ops_event(
            settings,
            component="ingestion",
            event_type="raw_pgns_persisted",
            source=settings.source,
            profile=profile,
            metadata={
                "inserted": raw_pgns_inserted,
                "computed": raw_pgns_hashed,
                "matched": raw_pgns_matched,
                "total": len(games_to_process),
            },
        )
        if postgres_pgns_active:
            with postgres_connection(settings) as pg_conn:
                if pg_conn is None:
                    logger.warning(
                        "Postgres raw PGN mirror enabled but connection unavailable"
                    )
                else:
                    init_pgn_schema(pg_conn)
                    try:
                        postgres_raw_pgns_inserted = upsert_postgres_raw_pgns(
                            pg_conn,
                            cast(list[Mapping[str, object]], games_to_process),
                        )
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Postgres raw PGN upsert failed: %s", exc)
            _emit_progress(
                progress,
                "postgres_raw_pgns_persisted",
                source=settings.source,
                inserted=postgres_raw_pgns_inserted,
                total=len(games_to_process),
            )
            record_ops_event(
                settings,
                component="ingestion",
                event_type="postgres_raw_pgns_persisted",
                source=settings.source,
                profile=profile,
                metadata={
                    "inserted": postgres_raw_pgns_inserted,
                    "total": len(games_to_process),
                },
            )

    logger.info(
        "Raw PGNs persisted: raw_pgns_inserted=%s raw_pgns_hashed=%s raw_pgns_matched=%s source=%s total=%s",
        raw_pgns_inserted,
        raw_pgns_hashed,
        raw_pgns_matched,
        settings.source,
        len(games_to_process),
    )

    _emit_progress(
        progress,
        "positions_ready",
        source=settings.source,
        positions=len(positions),
    )

    tactics_count = 0
    postgres_written = 0
    postgres_synced = 0
    analysis_complete = False
    total_positions = len(positions)
    progress_every = max(1, total_positions // 20) if total_positions else 1
    analysis_pg_enabled = postgres_analysis_enabled(settings)
    with postgres_connection(settings) as pg_conn:
        if pg_conn is not None and analysis_pg_enabled:
            init_analysis_schema(pg_conn)
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
                if pg_conn is not None and analysis_pg_enabled:
                    try:
                        upsert_analysis_tactic_with_outcome(
                            pg_conn,
                            tactic_row,
                            outcome_row,
                        )
                        postgres_written += 1
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Postgres analysis upsert failed: %s", exc)
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
        if pg_conn is not None and analysis_pg_enabled and postgres_written == 0:
            postgres_synced = _sync_postgres_analysis_results(conn, pg_conn, settings)
            postgres_written += postgres_synced
    analysis_complete = True
    if analysis_complete:
        _clear_analysis_checkpoint(analysis_checkpoint_path)
    record_ops_event(
        settings,
        component="analysis",
        event_type="analysis_complete",
        source=settings.source,
        profile=profile,
        metadata={
            "positions_analyzed": total_positions,
            "tactics_detected": tactics_count,
            "resume_index": resume_index,
            "postgres_tactics_written": postgres_written,
            "postgres_tactics_synced": postgres_synced,
        },
    )
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

    record_ops_event(
        settings,
        component=settings.run_context,
        event_type="daily_game_sync_complete",
        source=settings.source,
        profile=profile,
        metadata={
            "fetched_games": len(games),
            "raw_pgns_inserted": raw_pgns_inserted,
            "postgres_raw_pgns_inserted": postgres_raw_pgns_inserted,
            "positions": len(positions),
            "tactics": tactics_count,
            "postgres_tactics_written": postgres_written,
            "postgres_tactics_synced": postgres_synced,
            "metrics_version": metrics_version,
            "backfill": backfill_mode,
        },
    )

    return {
        "source": settings.source,
        "user": settings.user,
        "fetched_games": len(games),
        "raw_pgns_inserted": raw_pgns_inserted,
        "raw_pgns_hashed": raw_pgns_hashed,
        "raw_pgns_matched": raw_pgns_matched,
        "postgres_raw_pgns_inserted": postgres_raw_pgns_inserted,
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
    store: BaseDbStore | None = None,
) -> dict[str, object]:
    normalized_source = None if source in (None, "all") else source
    settings = settings or get_settings(source=normalized_source)
    if normalized_source:
        settings.source = normalized_source
    settings.apply_source_defaults()
    if store is None:
        store = DuckDbStore(
            BaseDbStoreContext(settings=settings, logger=logger),
            db_path=settings.duckdb_path,
        )
    return store.get_dashboard_payload(
        source=normalized_source,
        motif=motif,
        rating_bucket=rating_bucket,
        time_control=time_control,
        start_date=start_date,
        end_date=end_date,
    )
