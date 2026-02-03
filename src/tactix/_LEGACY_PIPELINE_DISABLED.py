_LEGACY_PIPELINE_DISABLED = """
import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TypedDict, cast

from tactix.base_db_store import BaseDbStore, BaseDbStoreContext
from tactix.chess_clients.base_chess_client import BaseChessClient
from tactix.chess_clients.chesscom_client import (
    ChesscomClient,
    ChesscomClientContext,
    ChesscomFetchRequest,
    ChesscomFetchResult,
)
from tactix.chess_clients.chesscom_client import (
    read_cursor as read_chesscom_cursor,
)
from tactix.chess_clients.chesscom_client import (
    write_cursor as write_chesscom_cursor,
)
from tactix.config import Settings, get_settings
from tactix.db.duckdb_store import (
    DuckDbStore,
    delete_game_rows,
    fetch_latest_pgn_hashes,
    fetch_latest_raw_pgns,
    fetch_metrics,
    fetch_position_counts,
    fetch_positions_for_games,
    fetch_recent_tactics,
    fetch_unanalyzed_positions,
    get_connection,
    get_schema_version,
    hash_pgn,
    init_schema,
    insert_positions,
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
from tactix.prepare_pgn__chess import (
    extract_game_id,
    extract_last_timestamp_ms,
    latest_timestamp,
    split_pgn_chunks,
)
from tactix.extract_positions__pgn import extract_positions
from tactix.postgres_store import (
    init_analysis_schema,
    init_pgn_schema,
    postgres_analysis_enabled,
    postgres_connection,
    postgres_pgns_enabled,
    record_ops_event,
    upsert_analysis_tactic_with_outcome,
    upsert_postgres_raw_pgns,
)
from tactix.run_stockfish__engine import StockfishEngine
from tactix.analyze_tactics__positions import analyze_position
from tactix.utils.logger import get_logger
from tactix.utils.source import normalized_source

logger = get_logger(__name__)
ANALYSIS_PROGRESS_BUCKETS = 20
DEFAULT_SYNC_LIMIT = 50
INDEX_OFFSET = 1
RESUME_INDEX_START = 0
SINGLE_PGN_CHUNK = 1
ZERO_COUNT = 0
LICHESS_BLACK_PROFILES = {"bullet", "blitz", "rapid", "classical", "correspondence"}
CHESSCOM_BLACK_PROFILES = {
    "bullet",
    "blitz",
    "rapid",
    "classical",
    "correspondence",
    "daily",
}


class GameRow(TypedDict):
    game_id: str
    user: str
    source: str
    fetched_at: datetime
    pgn: str
    last_timestamp_ms: int


ProgressCallback = Callable[[dict[str, object]], None]


@dataclass(slots=True)
class FetchContext:
    raw_games: list[Mapping[str, object]]
    since_ms: int
    cursor_before: str | None = None
    cursor_value: str | None = None
    next_cursor: str | None = None
    chesscom_result: ChesscomFetchResult | None = None
    last_timestamp_ms: int = 0


@dataclass(slots=True)
class AnalysisPrepResult:
    positions: list[dict[str, object]]
    resume_index: int
    analysis_signature: str
    raw_pgns_inserted: int
    raw_pgns_hashed: int
    raw_pgns_matched: int
    postgres_raw_pgns_inserted: int


@dataclass(slots=True)
class DailyAnalysisResult:
    total_positions: int
    tactics_count: int
    postgres_written: int
    postgres_synced: int
    metrics_version: int


def _coerce_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
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
        fetched_at = datetime.now(UTC)
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
        expanded.extend(_expand_single_pgn_row(row, settings))
    return expanded


def _expand_single_pgn_row(row: GameRow, settings: Settings) -> list[GameRow]:
    pgn_text = row.get("pgn", "")
    chunks = split_pgn_chunks(pgn_text)
    if len(chunks) <= SINGLE_PGN_CHUNK:
        return [row]
    return [_build_chunk_row(row, chunk, settings) for chunk in chunks]


def _build_chunk_row(row: GameRow, chunk: str, settings: Settings) -> GameRow:
    return cast(
        GameRow,
        {
            "game_id": extract_game_id(chunk),
            "user": row.get("user") or settings.user,
            "source": row.get("source") or settings.source,
            "fetched_at": row.get("fetched_at"),
            "pgn": chunk,
            "last_timestamp_ms": extract_last_timestamp_ms(chunk),
        },
    )


def _resolve_side_to_move_filter(settings: Settings) -> str | None:
    source = normalized_source(settings.source)
    profile = _normalized_profile_for_source(settings, source)
    black_profiles = _black_profiles_for_source(source)
    if not profile or black_profiles is None:
        return None
    return _side_filter_for_profile(profile, black_profiles)


def _normalized_profile_for_source(settings: Settings, source: str) -> str:
    profiles = {
        "lichess": settings.lichess_profile or settings.rapid_perf,
        "chesscom": settings.chesscom.profile or settings.chesscom.time_class,
    }
    raw_profile = profiles.get(source)
    return (raw_profile or "").strip().lower()


def _black_profiles_for_source(source: str) -> set[str] | None:
    if source == "lichess":
        return LICHESS_BLACK_PROFILES
    if source == "chesscom":
        return CHESSCOM_BLACK_PROFILES
    return None


def _side_filter_for_profile(profile: str, black_profiles: set[str]) -> str | None:
    return "black" if profile in black_profiles else None


def _emit_progress(progress: ProgressCallback | None, step: str, **fields: object) -> None:
    if progress is None:
        return
    payload: dict[str, object] = {"step": step, "timestamp": time.time()}
    payload.update(fields)
    progress(payload)


def _build_pipeline_settings(
    settings: Settings | None,
    source: str | None = None,
    profile: str | None = None,
) -> Settings:
    settings = settings or get_settings(source=source, profile=profile)
    if source:
        settings.source = source
    settings.apply_source_defaults()
    if profile is not None:
        settings.apply_lichess_profile(profile)
        settings.apply_chesscom_profile(profile)
    settings.ensure_dirs()
    return settings


def _build_chess_client(
    settings: Settings,
    client: BaseChessClient | None,
) -> BaseChessClient:
    if client is not None:
        return client
    if settings.source == "chesscom":
        return ChesscomClient(ChesscomClientContext(settings=settings, logger=logger))
    return LichessClient(LichessClientContext(settings=settings, logger=logger))


def _fetch_incremental_games(
    settings: Settings,
    client: BaseChessClient,
    backfill_mode: bool,
    window_start_ms: int | None,
    window_end_ms: int | None,
) -> FetchContext:
    if settings.source == "chesscom":
        return _fetch_chesscom_games(settings, client, backfill_mode)
    return _fetch_lichess_games(
        settings,
        client,
        backfill_mode,
        window_start_ms,
        window_end_ms,
    )


def _fetch_chesscom_games(
    settings: Settings,
    client: BaseChessClient,
    backfill_mode: bool,
) -> FetchContext:
    cursor_before = read_chesscom_cursor(settings.checkpoint_path)
    cursor_value = None if backfill_mode else cursor_before
    last_timestamp_value = _cursor_last_timestamp(cursor_value)
    chesscom_result = _request_chesscom_games(client, cursor_value, backfill_mode)
    raw_games = _chesscom_raw_games(chesscom_result)
    next_cursor = chesscom_result.next_cursor or cursor_value
    last_timestamp_value = chesscom_result.last_timestamp_ms
    return FetchContext(
        raw_games=raw_games,
        since_ms=ZERO_COUNT,
        cursor_before=cursor_before,
        cursor_value=cursor_value,
        next_cursor=next_cursor,
        chesscom_result=chesscom_result,
        last_timestamp_ms=last_timestamp_value,
    )


def _cursor_last_timestamp(cursor_value: str | None) -> int:
    if not cursor_value:
        return 0
    try:
        return int(cursor_value.split(":", 1)[0])
    except ValueError:
        return 0


def _request_chesscom_games(
    client: BaseChessClient, cursor_value: str | None, backfill_mode: bool
) -> ChesscomFetchResult:
    return client.fetch_incremental_games(
        ChesscomFetchRequest(cursor=cursor_value, full_history=backfill_mode)
    )


def _chesscom_raw_games(chesscom_result: ChesscomFetchResult) -> list[Mapping[str, object]]:
    return [cast(Mapping[str, object], row) for row in chesscom_result.games]


def _fetch_lichess_games(
    settings: Settings,
    client: BaseChessClient,
    backfill_mode: bool,
    window_start_ms: int | None,
    window_end_ms: int | None,
) -> FetchContext:
    checkpoint_before = read_checkpoint(settings.checkpoint_path)
    since_ms = window_start_ms if backfill_mode else checkpoint_before
    if since_ms is None:
        since_ms = ZERO_COUNT
    until_ms = window_end_ms if backfill_mode else None
    raw_games = [
        cast(Mapping[str, object], row)
        for row in client.fetch_incremental_games(
            LichessFetchRequest(since_ms=since_ms, until_ms=until_ms)
        ).games
    ]
    return FetchContext(
        raw_games=raw_games,
        since_ms=since_ms,
        cursor_before=None,
        cursor_value=None,
        next_cursor=None,
        chesscom_result=None,
        last_timestamp_ms=since_ms,
    )


def _emit_daily_sync_start(
    settings: Settings,
    progress: ProgressCallback | None,
    profile: str | None,
    backfill_mode: bool,
    window_start_ms: int | None,
    window_end_ms: int | None,
) -> None:
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


def _normalize_and_expand_games(
    raw_games: list[Mapping[str, object]],
    settings: Settings,
) -> list[GameRow]:
    games = [_normalize_game_row(game, settings) for game in raw_games]
    games = _expand_pgn_rows(games, settings)
    return _dedupe_games(games)


def _emit_backfill_window_filtered(
    settings: Settings,
    progress: ProgressCallback | None,
    filtered: int,
    window_start_ms: int | None,
    window_end_ms: int | None,
) -> None:
    if not filtered:
        return
    logger.info(
        "Filtered %s games outside backfill window for source=%s",
        filtered,
        settings.source,
    )
    _emit_progress(
        progress,
        "backfill_window_filtered",
        source=settings.source,
        filtered=filtered,
        backfill_start_ms=window_start_ms,
        backfill_end_ms=window_end_ms,
    )


def _prepare_games_for_sync(
    settings: Settings,
    client: BaseChessClient,
    backfill_mode: bool,
    window_start_ms: int | None,
    window_end_ms: int | None,
    progress: ProgressCallback | None,
) -> tuple[list[GameRow], FetchContext, int, int]:
    fetch_context = _fetch_incremental_games(
        settings,
        client,
        backfill_mode,
        window_start_ms,
        window_end_ms,
    )
    games = _normalize_and_expand_games(fetch_context.raw_games, settings)
    games, window_filtered = _filter_games_for_window(
        games,
        window_start_ms,
        window_end_ms,
    )
    _maybe_emit_window_filtered(
        settings,
        progress,
        backfill_mode,
        window_filtered,
        window_start_ms,
        window_end_ms,
    )
    last_timestamp_value = _resolve_last_timestamp_value(games, fetch_context.last_timestamp_ms)
    _emit_fetch_progress(
        settings,
        progress,
        fetch_context,
        backfill_mode,
        window_start_ms,
        window_end_ms,
        len(games),
    )
    return games, fetch_context, window_filtered, last_timestamp_value


def _filter_games_for_window(
    games: list[GameRow],
    window_start_ms: int | None,
    window_end_ms: int | None,
) -> tuple[list[GameRow], int]:
    pre_window_count = len(games)
    filtered = _filter_games_by_window(games, window_start_ms, window_end_ms)
    return filtered, pre_window_count - len(filtered)


def _maybe_emit_window_filtered(
    settings: Settings,
    progress: ProgressCallback | None,
    backfill_mode: bool,
    window_filtered: int,
    window_start_ms: int | None,
    window_end_ms: int | None,
) -> None:
    if not backfill_mode or not window_filtered:
        return
    _emit_backfill_window_filtered(
        settings,
        progress,
        window_filtered,
        window_start_ms,
        window_end_ms,
    )


def _resolve_last_timestamp_value(games: list[GameRow], fallback: int) -> int:
    if not games:
        return fallback
    return latest_timestamp(games) or fallback


def _emit_fetch_progress(
    settings: Settings,
    progress: ProgressCallback | None,
    fetch_context: FetchContext,
    backfill_mode: bool,
    window_start_ms: int | None,
    window_end_ms: int | None,
    fetched_games: int,
) -> None:
    _emit_progress(
        progress,
        "fetch_games",
        source=settings.source,
        fetched_games=fetched_games,
        since_ms=fetch_context.since_ms,
        cursor=fetch_context.next_cursor or fetch_context.cursor_value,
        backfill=backfill_mode,
        backfill_start_ms=window_start_ms,
        backfill_end_ms=window_end_ms,
    )


def _build_no_games_payload(
    settings: Settings,
    conn,
    backfill_mode: bool,
    fetch_context: FetchContext,
    last_timestamp_value: int,
    window_filtered: int,
) -> dict[str, object]:
    metrics_version = _update_metrics_and_version(settings, conn)
    checkpoint_ms = _no_games_checkpoint(settings, backfill_mode, fetch_context)
    cursor = _no_games_cursor(backfill_mode, fetch_context)
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
        "checkpoint_ms": checkpoint_ms,
        "cursor": cursor,
        "last_timestamp_ms": last_timestamp_value or fetch_context.since_ms,
        "since_ms": fetch_context.since_ms,
        "window_filtered": window_filtered,
    }


def _no_games_checkpoint(
    settings: Settings, backfill_mode: bool, fetch_context: FetchContext
) -> int | None:
    if backfill_mode or settings.source == "chesscom":
        return None
    return fetch_context.since_ms


def _no_games_cursor(backfill_mode: bool, fetch_context: FetchContext) -> str | None:
    if backfill_mode:
        return fetch_context.cursor_before
    return fetch_context.next_cursor or fetch_context.cursor_value


def _handle_no_games(
    settings: Settings,
    conn,
    progress: ProgressCallback | None,
    backfill_mode: bool,
    fetch_context: FetchContext,
    last_timestamp_value: int,
    window_filtered: int,
) -> dict[str, object]:
    logger.info(
        "No new games for source=%s at checkpoint=%s",
        settings.source,
        fetch_context.since_ms,
    )
    _emit_progress(
        progress,
        "no_games",
        source=settings.source,
        message="No new games to process",
    )
    return _build_no_games_payload(
        settings,
        conn,
        backfill_mode,
        fetch_context,
        last_timestamp_value,
        window_filtered,
    )


def _apply_backfill_filter(
    conn,
    games: list[GameRow],
    backfill_mode: bool,
    source: str,
) -> tuple[list[GameRow], list[GameRow]]:
    if not backfill_mode:
        return games, []
    return _filter_backfill_games(conn, games, source)


def _log_skipped_backfill(settings: Settings, skipped_games: list[GameRow]) -> None:
    if skipped_games:
        logger.info(
            "Skipping %s historical games already processed for source=%s",
            len(skipped_games),
            settings.source,
        )


def _build_no_games_after_dedupe_payload(
    settings: Settings,
    conn,
    backfill_mode: bool,
    fetch_context: FetchContext,
    last_timestamp_value: int,
    games: list[GameRow],
    window_filtered: int,
) -> dict[str, object]:
    metrics_version = _update_metrics_and_version(settings, conn)
    checkpoint_ms, last_timestamp_value = _apply_no_games_dedupe_checkpoint(
        settings,
        backfill_mode,
        fetch_context,
        last_timestamp_value,
    )
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
        "checkpoint_ms": checkpoint_ms,
        "cursor": _no_games_cursor(backfill_mode, fetch_context),
        "last_timestamp_ms": last_timestamp_value,
        "since_ms": fetch_context.since_ms,
        "window_filtered": window_filtered,
    }


def _apply_no_games_dedupe_checkpoint(
    settings: Settings,
    backfill_mode: bool,
    fetch_context: FetchContext,
    last_timestamp_value: int,
) -> tuple[int | None, int]:
    if backfill_mode:
        return None, last_timestamp_value
    if settings.source == "chesscom":
        write_chesscom_cursor(settings.checkpoint_path, fetch_context.next_cursor)
        return None, last_timestamp_value
    checkpoint_value = max(fetch_context.since_ms, last_timestamp_value)
    write_checkpoint(settings.checkpoint_path, checkpoint_value)
    return checkpoint_value, checkpoint_value


def _handle_no_games_after_dedupe(
    settings: Settings,
    conn,
    backfill_mode: bool,
    fetch_context: FetchContext,
    last_timestamp_value: int,
    games: list[GameRow],
    window_filtered: int,
) -> dict[str, object]:
    logger.info(
        "No new games to process after backfill dedupe for source=%s",
        settings.source,
    )
    return _build_no_games_after_dedupe_payload(
        settings,
        conn,
        backfill_mode,
        fetch_context,
        last_timestamp_value,
        games,
        window_filtered,
    )


def _update_daily_checkpoint(
    settings: Settings,
    backfill_mode: bool,
    fetch_context: FetchContext,
    games: list[GameRow],
    last_timestamp_value: int,
) -> tuple[int | None, int]:
    if backfill_mode:
        return None, last_timestamp_value
    if settings.source == "chesscom":
        return _update_chesscom_checkpoint(settings, fetch_context, games, last_timestamp_value)
    return _update_lichess_checkpoint(settings, fetch_context, games)


def _update_chesscom_checkpoint(
    settings: Settings,
    fetch_context: FetchContext,
    games: list[GameRow],
    last_timestamp_value: int,
) -> tuple[int | None, int]:
    write_chesscom_cursor(settings.checkpoint_path, fetch_context.next_cursor)
    last_timestamp_value = _resolve_chesscom_last_timestamp(
        fetch_context,
        games,
        last_timestamp_value,
    )
    return None, last_timestamp_value


def _resolve_chesscom_last_timestamp(
    fetch_context: FetchContext,
    games: list[GameRow],
    last_timestamp_value: int,
) -> int:
    if fetch_context.chesscom_result:
        return fetch_context.chesscom_result.last_timestamp_ms
    if games:
        return latest_timestamp(games) or last_timestamp_value
    return last_timestamp_value


def _update_lichess_checkpoint(
    settings: Settings,
    fetch_context: FetchContext,
    games: list[GameRow],
) -> tuple[int | None, int]:
    checkpoint_value = max(fetch_context.since_ms, latest_timestamp(games))
    write_checkpoint(settings.checkpoint_path, checkpoint_value)
    return checkpoint_value, checkpoint_value


def _build_daily_sync_payload(
    settings: Settings,
    fetch_context: FetchContext,
    games: list[GameRow],
    raw_pgns_inserted: int,
    raw_pgns_hashed: int,
    raw_pgns_matched: int,
    postgres_raw_pgns_inserted: int,
    positions_count: int,
    tactics_count: int,
    metrics_version: int,
    checkpoint_value: int | None,
    last_timestamp_value: int,
    backfill_mode: bool,
) -> dict[str, object]:
    return {
        "source": settings.source,
        "user": settings.user,
        "fetched_games": len(games),
        "raw_pgns_inserted": raw_pgns_inserted,
        "raw_pgns_hashed": raw_pgns_hashed,
        "raw_pgns_matched": raw_pgns_matched,
        "postgres_raw_pgns_inserted": postgres_raw_pgns_inserted,
        "positions": positions_count,
        "tactics": tactics_count,
        "metrics_version": metrics_version,
        "checkpoint_ms": checkpoint_value,
        "cursor": fetch_context.cursor_before
        if backfill_mode
        else (fetch_context.next_cursor or fetch_context.cursor_value),
        "last_timestamp_ms": last_timestamp_value,
        "since_ms": fetch_context.since_ms,
    }


def _is_backfill_mode(window_start_ms: int | None, window_end_ms: int | None) -> bool:
    return window_start_ms is not None or window_end_ms is not None


def _log_raw_pgns_persisted(
    settings: Settings,
    raw_pgns_inserted: int,
    raw_pgns_hashed: int,
    raw_pgns_matched: int,
    games_to_process: list[GameRow],
) -> None:
    logger.info(
        "Raw PGNs persisted: raw_pgns_inserted=%s raw_pgns_hashed=%s "
        "raw_pgns_matched=%s source=%s total=%s",
        raw_pgns_inserted,
        raw_pgns_hashed,
        raw_pgns_matched,
        settings.source,
        len(games_to_process),
    )


def _emit_positions_ready(
    settings: Settings,
    progress: ProgressCallback | None,
    positions: list[dict[str, object]],
) -> None:
    _emit_progress(
        progress,
        "positions_ready",
        source=settings.source,
        positions=len(positions),
    )


def _run_analysis_and_metrics(
    conn,
    settings: Settings,
    positions: list[dict[str, object]],
    resume_index: int,
    analysis_checkpoint_path,
    analysis_signature: str,
    progress: ProgressCallback | None,
    profile: str | None,
) -> DailyAnalysisResult:
    total_positions = len(positions)
    tactics_count, postgres_written, postgres_synced = _analyze_positions_with_progress(
        conn,
        settings,
        positions,
        resume_index,
        analysis_checkpoint_path,
        analysis_signature,
        progress,
    )
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
    metrics_version = _update_metrics_and_version(settings, conn)
    _emit_progress(
        progress,
        "metrics_refreshed",
        source=settings.source,
        metrics_version=metrics_version,
        message="Metrics refreshed",
    )
    return DailyAnalysisResult(
        total_positions=total_positions,
        tactics_count=tactics_count,
        postgres_written=postgres_written,
        postgres_synced=postgres_synced,
        metrics_version=metrics_version,
    )


def _record_daily_sync_complete(
    settings: Settings,
    profile: str | None,
    games: list[GameRow],
    raw_pgns_inserted: int,
    postgres_raw_pgns_inserted: int,
    positions_count: int,
    tactics_count: int,
    postgres_written: int,
    postgres_synced: int,
    metrics_version: int,
    backfill_mode: bool,
) -> None:
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
            "positions": positions_count,
            "tactics": tactics_count,
            "postgres_tactics_written": postgres_written,
            "postgres_tactics_synced": postgres_synced,
            "metrics_version": metrics_version,
            "backfill": backfill_mode,
        },
    )


def _update_metrics_and_version(settings: Settings, conn) -> int:
    update_metrics_summary(conn)
    metrics_version = write_metrics_version(conn)
    settings.metrics_version_file.write_text(str(metrics_version))
    return metrics_version


def _persist_raw_pgns(
    conn,
    games_to_process: list[GameRow],
    settings: Settings,
    progress: ProgressCallback | None,
    profile: str | None,
    *,
    delete_existing: bool,
    emit_start: bool,
) -> tuple[int, int, int]:
    if emit_start:
        _emit_progress(
            progress,
            "raw_pgns",
            source=settings.source,
            message="Persisting raw PGNs",
        )
    if delete_existing:
        delete_game_rows(conn, [game["game_id"] for game in games_to_process])
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
    return raw_pgns_inserted, raw_pgns_hashed, raw_pgns_matched


def _upsert_postgres_raw_pgns_if_enabled(
    settings: Settings,
    games_to_process: list[GameRow],
    progress: ProgressCallback | None,
    profile: str | None,
) -> int:
    if not postgres_pgns_enabled(settings):
        return 0
    inserted = 0
    with postgres_connection(settings) as pg_conn:
        if pg_conn is None:
            logger.warning("Postgres raw PGN mirror enabled but connection unavailable")
        else:
            init_pgn_schema(pg_conn)
            try:
                inserted = upsert_postgres_raw_pgns(
                    pg_conn,
                    cast(list[Mapping[str, object]], games_to_process),
                )
            except Exception as exc:
                logger.warning("Postgres raw PGN upsert failed: %s", exc)
    _emit_progress(
        progress,
        "postgres_raw_pgns_persisted",
        source=settings.source,
        inserted=inserted,
        total=len(games_to_process),
    )
    record_ops_event(
        settings,
        component="ingestion",
        event_type="postgres_raw_pgns_persisted",
        source=settings.source,
        profile=profile,
        metadata={
            "inserted": inserted,
            "total": len(games_to_process),
        },
    )
    return inserted


def _persist_and_extract_positions(
    conn,
    settings: Settings,
    games_to_process: list[GameRow],
    progress: ProgressCallback | None,
    profile: str | None,
    game_ids: list[str],
) -> tuple[list[dict[str, object]], str, tuple[int, int, int], int]:
    raw_pgns_inserted, raw_pgns_hashed, raw_pgns_matched = _persist_raw_pgns(
        conn,
        games_to_process,
        settings,
        progress,
        profile,
        delete_existing=True,
        emit_start=True,
    )
    postgres_raw_pgns_inserted = _upsert_postgres_raw_pgns_if_enabled(
        settings,
        games_to_process,
        progress,
        profile,
    )
    _emit_progress(
        progress,
        "extract_positions",
        source=settings.source,
        message="Extracting positions",
    )
    positions = _extract_positions_from_games(conn, games_to_process, settings)
    analysis_signature = _analysis_signature(game_ids, len(positions), settings.source)
    return (
        positions,
        analysis_signature,
        (raw_pgns_inserted, raw_pgns_hashed, raw_pgns_matched),
        postgres_raw_pgns_inserted,
    )


def _refresh_raw_pgns_for_existing_positions(
    conn,
    settings: Settings,
    games_to_process: list[GameRow],
    progress: ProgressCallback | None,
    profile: str | None,
) -> tuple[tuple[int, int, int], int]:
    raw_pgns_inserted, raw_pgns_hashed, raw_pgns_matched = _persist_raw_pgns(
        conn,
        games_to_process,
        settings,
        progress,
        profile,
        delete_existing=False,
        emit_start=False,
    )
    postgres_raw_pgns_inserted = _upsert_postgres_raw_pgns_if_enabled(
        settings,
        games_to_process,
        progress,
        profile,
    )
    return (raw_pgns_inserted, raw_pgns_hashed, raw_pgns_matched), postgres_raw_pgns_inserted


def _prepare_analysis_inputs(
    conn,
    settings: Settings,
    games_to_process: list[GameRow],
    progress: ProgressCallback | None,
    profile: str | None,
) -> AnalysisPrepResult:
    game_ids = [game["game_id"] for game in games_to_process]
    analysis_checkpoint_path = settings.analysis_checkpoint_path
    positions, resume_index, analysis_signature = _load_resume_positions(
        conn, analysis_checkpoint_path, game_ids, settings.source
    )
    if positions:
        (raw_pgns_inserted, raw_pgns_hashed, raw_pgns_matched), postgres_raw_pgns_inserted = (
            _refresh_raw_pgns_for_existing_positions(
                conn,
                settings,
                games_to_process,
                progress,
                profile,
            )
        )
        return AnalysisPrepResult(
            positions=positions,
            resume_index=resume_index,
            analysis_signature=analysis_signature,
            raw_pgns_inserted=raw_pgns_inserted,
            raw_pgns_hashed=raw_pgns_hashed,
            raw_pgns_matched=raw_pgns_matched,
            postgres_raw_pgns_inserted=postgres_raw_pgns_inserted,
        )

    positions, analysis_signature, raw_metrics, postgres_raw_pgns_inserted = (
        _persist_and_extract_positions(
            conn,
            settings,
            games_to_process,
            progress,
            profile,
            game_ids,
        )
    )
    raw_pgns_inserted, raw_pgns_hashed, raw_pgns_matched = raw_metrics
    return AnalysisPrepResult(
        positions=positions,
        resume_index=resume_index,
        analysis_signature=analysis_signature,
        raw_pgns_inserted=raw_pgns_inserted,
        raw_pgns_hashed=raw_pgns_hashed,
        raw_pgns_matched=raw_pgns_matched,
        postgres_raw_pgns_inserted=postgres_raw_pgns_inserted,
    )


def _extract_positions_from_games(
    conn,
    games_to_process: list[GameRow],
    settings: Settings,
) -> list[dict[str, object]]:
    side_to_move_filter = _resolve_side_to_move_filter(settings)
    positions: list[dict[str, object]] = []
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
    return positions


def _load_resume_positions(
    conn,
    analysis_checkpoint_path,
    game_ids: list[str],
    source: str,
) -> tuple[list[dict[str, object]], int, str]:
    positions: list[dict[str, object]] = []
    resume_index = -1
    analysis_signature = ""
    if analysis_checkpoint_path.exists():
        existing_positions = fetch_positions_for_games(conn, game_ids)
        if existing_positions:
            analysis_signature = _analysis_signature(game_ids, len(existing_positions), source)
            resume_index = _read_analysis_checkpoint(analysis_checkpoint_path, analysis_signature)
            if resume_index >= RESUME_INDEX_START:
                logger.info("Resuming analysis at index=%s for source=%s", resume_index, source)
                positions = existing_positions
            else:
                _clear_analysis_checkpoint(analysis_checkpoint_path)
        else:
            _clear_analysis_checkpoint(analysis_checkpoint_path)
    return positions, resume_index, analysis_signature


def _maybe_upsert_postgres_analysis(
    pg_conn,
    analysis_pg_enabled: bool,
    tactic_row: dict[str, object],
    outcome_row: dict[str, object],
) -> bool:
    if pg_conn is None or not analysis_pg_enabled:
        return False
    try:
        upsert_analysis_tactic_with_outcome(
            pg_conn,
            tactic_row,
            outcome_row,
        )
    except Exception as exc:
        logger.warning("Postgres analysis upsert failed: %s", exc)
        return False
    else:
        return True


def _analysis_progress_interval(total_positions: int) -> int:
    if total_positions:
        return max(1, total_positions // ANALYSIS_PROGRESS_BUCKETS)
    return INDEX_OFFSET


def _maybe_write_analysis_checkpoint(
    analysis_checkpoint_path,
    analysis_signature: str,
    index: int,
) -> None:
    if analysis_checkpoint_path is None:
        return
    _write_analysis_checkpoint(analysis_checkpoint_path, analysis_signature, index)


def _maybe_emit_analysis_progress(
    progress: ProgressCallback | None,
    settings: Settings,
    idx: int,
    total_positions: int,
    progress_every: int,
) -> None:
    if not progress:
        return
    if idx == total_positions - INDEX_OFFSET or (idx + INDEX_OFFSET) % progress_every == ZERO_COUNT:
        _emit_progress(
            progress,
            "analyze_positions",
            source=settings.source,
            analyzed=idx + INDEX_OFFSET,
            total=total_positions,
        )


def _process_analysis_position(
    conn,
    settings: Settings,
    engine: StockfishEngine,
    pos: dict[str, object],
    idx: int,
    resume_index: int,
    analysis_checkpoint_path,
    analysis_signature: str,
    progress: ProgressCallback | None,
    total_positions: int,
    progress_every: int,
    pg_conn,
    analysis_pg_enabled: bool,
) -> tuple[int, int]:
    if idx <= resume_index:
        return 0, 0
    result = _analyse_with_retries(engine, pos, settings)
    if result is None:
        _maybe_write_analysis_checkpoint(analysis_checkpoint_path, analysis_signature, idx)
        return 0, 0
    tactic_row, outcome_row = result
    upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
    postgres_delta = (
        1
        if _maybe_upsert_postgres_analysis(pg_conn, analysis_pg_enabled, tactic_row, outcome_row)
        else 0
    )
    _maybe_write_analysis_checkpoint(analysis_checkpoint_path, analysis_signature, idx)
    _maybe_emit_analysis_progress(progress, settings, idx, total_positions, progress_every)
    return 1, postgres_delta


def _run_analysis_loop(
    conn,
    settings: Settings,
    positions: list[dict[str, object]],
    resume_index: int,
    analysis_checkpoint_path,
    analysis_signature: str,
    progress: ProgressCallback | None,
    pg_conn,
    analysis_pg_enabled: bool,
) -> tuple[int, int]:
    total_positions = len(positions)
    progress_every = _analysis_progress_interval(total_positions)
    tactics_count = 0
    postgres_written = 0
    with StockfishEngine(settings) as engine:
        for idx, pos in enumerate(positions):
            tactics_delta, postgres_delta = _process_analysis_position(
                conn,
                settings,
                engine,
                pos,
                idx,
                resume_index,
                analysis_checkpoint_path,
                analysis_signature,
                progress,
                total_positions,
                progress_every,
                pg_conn,
                analysis_pg_enabled,
            )
            tactics_count += tactics_delta
            postgres_written += postgres_delta
    return tactics_count, postgres_written


def _analyze_positions_with_progress(
    conn,
    settings: Settings,
    positions: list[dict[str, object]],
    resume_index: int,
    analysis_checkpoint_path,
    analysis_signature: str,
    progress: ProgressCallback | None,
) -> tuple[int, int, int]:
    analysis_pg_enabled = postgres_analysis_enabled(settings)
    with postgres_connection(settings) as pg_conn:
        _init_analysis_schema_if_needed(pg_conn, analysis_pg_enabled)
        tactics_count, postgres_written = _run_analysis_loop(
            conn,
            settings,
            positions,
            resume_index,
            analysis_checkpoint_path,
            analysis_signature,
            progress,
            pg_conn,
            analysis_pg_enabled,
        )
        postgres_synced, postgres_written = _maybe_sync_analysis_results(
            conn,
            settings,
            pg_conn,
            analysis_pg_enabled,
            postgres_written,
        )
    _maybe_clear_analysis_checkpoint(analysis_checkpoint_path)
    return tactics_count, postgres_written, postgres_synced


def _init_analysis_schema_if_needed(pg_conn, analysis_pg_enabled: bool) -> None:
    if pg_conn is not None and analysis_pg_enabled:
        init_analysis_schema(pg_conn)


def _maybe_sync_analysis_results(
    conn,
    settings: Settings,
    pg_conn,
    analysis_pg_enabled: bool,
    postgres_written: int,
) -> tuple[int, int]:
    if pg_conn is None or not analysis_pg_enabled or postgres_written != ZERO_COUNT:
        return 0, postgres_written
    postgres_synced = _sync_postgres_analysis_results(conn, pg_conn, settings)
    return postgres_synced, postgres_written + postgres_synced


def _maybe_clear_analysis_checkpoint(analysis_checkpoint_path) -> None:
    if analysis_checkpoint_path is not None:
        _clear_analysis_checkpoint(analysis_checkpoint_path)


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
    return [game for game in rows if _within_window(game, start_ms, end_ms)]


def _within_window(game: GameRow, start_ms: int | None, end_ms: int | None) -> bool:
    last_ts = game["last_timestamp_ms"]
    return (start_ms is None or last_ts >= start_ms) and (end_ms is None or last_ts < end_ms)


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
        if _should_skip_backfill(game, latest_hashes, position_counts):
            skipped.append(game)
        else:
            to_process.append(game)
    return to_process, skipped


def _should_skip_backfill(
    game: GameRow,
    latest_hashes: Mapping[str, str],
    position_counts: Mapping[str, int],
) -> bool:
    game_id = game["game_id"]
    current_hash = hash_pgn(game["pgn"])
    existing_hash = latest_hashes.get(game_id)
    return bool(
        existing_hash == current_hash and position_counts.get(game_id, ZERO_COUNT) > ZERO_COUNT
    )


def _compute_pgn_hashes(rows: list[GameRow], source: str) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for row in rows:
        game_id = row["game_id"]
        if game_id in hashes:
            raise ValueError(f"Duplicate game_id in raw PGN batch for source={source}: {game_id}")
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
    matched = _count_hash_matches(computed, stored)
    _raise_for_hash_mismatch(source, computed, stored, matched)
    return {"computed": len(computed), "matched": matched}


def _count_hash_matches(computed: Mapping[str, str], stored: Mapping[str, str]) -> int:
    return sum(1 for game_id, pgn_hash in computed.items() if stored.get(game_id) == pgn_hash)


def _raise_for_hash_mismatch(
    source: str,
    computed: Mapping[str, str],
    stored: Mapping[str, str],
    matched: int,
) -> None:
    if matched == len(computed):
        return
    missing = [game_id for game_id, pgn_hash in computed.items() if stored.get(game_id) != pgn_hash]
    missing_sorted = ", ".join(sorted(missing))
    raise ValueError(
        f"Raw PGN hash mismatch for source={source} expected={len(computed)} "
        f"matched={matched} missing={missing_sorted}"
    )


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
    settings = _build_pipeline_settings(settings, source=source, profile=profile)

    conn = get_connection(settings.duckdb_path)
    init_schema(conn)

    raw_pgns = fetch_latest_raw_pgns(conn, settings.source, limit)
    if not raw_pgns:
        return _empty_conversion_payload(settings)

    to_process = _filter_positions_to_process(conn, raw_pgns, settings)
    positions = _extract_positions_for_rows(to_process, settings)
    position_ids = insert_positions(conn, positions)
    _attach_position_ids(positions, position_ids)

    return _conversion_payload(settings, raw_pgns, to_process, positions)


def _empty_conversion_payload(settings: Settings) -> dict[str, object]:
    return {
        "source": settings.source,
        "games": 0,
        "inserted_games": 0,
        "positions": 0,
    }


def _filter_positions_to_process(
    conn,
    raw_pgns: list[dict[str, object]],
    settings: Settings,
) -> list[dict[str, object]]:
    game_ids = _collect_game_ids(raw_pgns)
    position_counts = fetch_position_counts(conn, game_ids, settings.source)
    return _filter_unprocessed_games(raw_pgns, position_counts)


def _conversion_payload(
    settings: Settings,
    raw_pgns: list[dict[str, object]],
    to_process: list[dict[str, object]],
    positions: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "source": settings.source,
        "games": len(raw_pgns),
        "inserted_games": len(to_process),
        "positions": len(positions),
    }


def _extract_positions_for_new_games(
    conn, settings: Settings, raw_pgns: list[dict[str, object]]
) -> tuple[list[dict[str, object]], list[str]]:
    game_ids = _collect_game_ids(raw_pgns)
    if not game_ids:
        return [], []
    position_counts = fetch_position_counts(conn, game_ids, settings.source)
    to_process = _filter_unprocessed_games(raw_pgns, position_counts)
    if not to_process:
        return [], []
    positions = _extract_positions_for_rows(to_process, settings)
    position_ids = insert_positions(conn, positions)
    _attach_position_ids(positions, position_ids)
    return positions, _collect_game_ids(to_process)


def _collect_game_ids(rows: list[dict[str, object]]) -> list[str]:
    return [str(row.get("game_id", "")) for row in rows if row.get("game_id")]


def _filter_unprocessed_games(
    raw_pgns: list[dict[str, object]],
    position_counts: dict[str, int],
) -> list[dict[str, object]]:
    return [
        row
        for row in raw_pgns
        if position_counts.get(str(row.get("game_id")), ZERO_COUNT) == ZERO_COUNT
    ]


def _extract_positions_for_rows(
    rows: list[dict[str, object]],
    settings: Settings,
) -> list[dict[str, object]]:
    positions: list[dict[str, object]] = []
    side_to_move_filter = _resolve_side_to_move_filter(settings)
    for row in rows:
        positions.extend(
            extract_positions(
                str(row.get("pgn", "")),
                str(row.get("user") or settings.user),
                str(row.get("source") or settings.source),
                game_id=str(row.get("game_id", "")),
                side_to_move_filter=side_to_move_filter,
            )
        )
    return positions


def _attach_position_ids(
    positions: list[dict[str, object]],
    position_ids: list[int],
) -> None:
    for pos, pos_id in zip(positions, position_ids, strict=False):
        pos["position_id"] = pos_id


def _collect_positions_for_monitor(
    conn,
    settings: Settings,
    raw_pgns: list[dict[str, object]],
) -> tuple[int, list[str], list[dict[str, object]]]:
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

    return positions_extracted, new_game_ids, positions_to_analyze


def _analyze_positions(
    conn, settings: Settings, positions: list[dict[str, object]]
) -> tuple[int, int]:
    if not positions:
        return 0, 0
    analysis_pg_enabled = postgres_analysis_enabled(settings)
    with postgres_connection(settings) as pg_conn:
        _init_analysis_schema_if_needed(pg_conn, analysis_pg_enabled)
        tactics_detected, postgres_written = _run_analysis_loop(
            conn,
            settings,
            positions,
            RESUME_INDEX_START - INDEX_OFFSET,
            None,
            "",
            None,
            pg_conn,
            analysis_pg_enabled,
        )
        postgres_synced, postgres_written = _maybe_sync_analysis_results(
            conn,
            settings,
            pg_conn,
            analysis_pg_enabled,
            postgres_written,
        )
    positions_analyzed = len(positions)
    record_ops_event(
        settings,
        component="analysis",
        event_type="analysis_complete",
        source=settings.source,
        profile=settings.lichess_profile or settings.chesscom.profile,
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
    limit: int = DEFAULT_SYNC_LIMIT,
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
        except Exception as exc:
            logger.warning("Postgres analysis sync failed: %s", exc)
    return synced


def run_monitor_new_positions(
    settings: Settings | None = None,
    source: str | None = None,
    profile: str | None = None,
    limit: int | None = None,
) -> dict[str, object]:
    settings = _build_pipeline_settings(settings, source=source, profile=profile)

    conn = get_connection(settings.duckdb_path)
    init_schema(conn)

    raw_pgns = fetch_latest_raw_pgns(conn, settings.source, limit)
    positions_extracted, new_game_ids, positions_to_analyze = _collect_positions_for_monitor(
        conn, settings, raw_pgns
    )

    positions_analyzed, tactics_detected = _analyze_positions(conn, settings, positions_to_analyze)

    metrics_version = _update_metrics_and_version(settings, conn)

    logger.info(
        "Monitor run complete: source=%s new_games=%s positions_extracted=%s "
        "positions_analyzed=%s tactics_detected=%s metrics_version=%s",
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


def _run_daily_game_sync(
    settings: Settings,
    client: BaseChessClient,
    progress: ProgressCallback | None,
    window_start_ms: int | None,
    window_end_ms: int | None,
    profile: str | None,
) -> dict[str, object]:
    backfill_mode = _is_backfill_mode(window_start_ms, window_end_ms)
    _emit_daily_sync_start(
        settings,
        progress,
        profile,
        backfill_mode,
        window_start_ms,
        window_end_ms,
    )
    games, fetch_context, window_filtered, last_timestamp_value = _prepare_games_for_sync(
        settings,
        client,
        backfill_mode,
        window_start_ms,
        window_end_ms,
        progress,
    )
    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    if not games:
        return _handle_no_games(
            settings,
            conn,
            progress,
            backfill_mode,
            fetch_context,
            last_timestamp_value,
            window_filtered,
        )
    games_to_process, skipped_games = _apply_backfill_filter(
        conn, games, backfill_mode, settings.source
    )
    _log_skipped_backfill(settings, skipped_games)
    if not games_to_process:
        return _handle_no_games_after_dedupe(
            settings,
            conn,
            backfill_mode,
            fetch_context,
            last_timestamp_value,
            games,
            window_filtered,
        )
    analysis_prep = _prepare_analysis_inputs(
        conn,
        settings,
        games_to_process,
        progress,
        profile,
    )
    analysis_checkpoint_path = settings.analysis_checkpoint_path
    _log_raw_pgns_persisted(
        settings,
        analysis_prep.raw_pgns_inserted,
        analysis_prep.raw_pgns_hashed,
        analysis_prep.raw_pgns_matched,
        games_to_process,
    )
    _emit_positions_ready(settings, progress, analysis_prep.positions)
    analysis_result = _run_analysis_and_metrics(
        conn,
        settings,
        analysis_prep.positions,
        analysis_prep.resume_index,
        analysis_checkpoint_path,
        analysis_prep.analysis_signature,
        progress,
        profile,
    )
    checkpoint_value, last_timestamp_value = _update_daily_checkpoint(
        settings,
        backfill_mode,
        fetch_context,
        games,
        last_timestamp_value,
    )
    _record_daily_sync_complete(
        settings,
        profile,
        games,
        analysis_prep.raw_pgns_inserted,
        analysis_prep.postgres_raw_pgns_inserted,
        analysis_result.total_positions,
        analysis_result.tactics_count,
        analysis_result.postgres_written,
        analysis_result.postgres_synced,
        analysis_result.metrics_version,
        backfill_mode,
    )
    return _build_daily_sync_payload(
        settings,
        fetch_context,
        games,
        analysis_prep.raw_pgns_inserted,
        analysis_prep.raw_pgns_hashed,
        analysis_prep.raw_pgns_matched,
        analysis_prep.postgres_raw_pgns_inserted,
        analysis_result.total_positions,
        analysis_result.tactics_count,
        analysis_result.metrics_version,
        checkpoint_value,
        last_timestamp_value,
        backfill_mode,
    )


def run_daily_game_sync(
    settings: Settings | None = None,
    source: str | None = None,
    progress: ProgressCallback | None = None,
    window_start_ms: int | None = None,
    window_end_ms: int | None = None,
    profile: str | None = None,
    client: BaseChessClient | None = None,
) -> dict[str, object]:
    settings = _build_pipeline_settings(settings, source=source, profile=profile)
    client = _build_chess_client(settings, client)
    return _run_daily_game_sync(
        settings,
        client,
        progress,
        window_start_ms,
        window_end_ms,
        profile,
    )


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

"""
