from __future__ import annotations

from tactix.chesscom_client import fetch_incremental_games as fetch_chesscom_games
from tactix.config import Settings, get_settings
from tactix.duckdb_store import (
    fetch_metrics,
    fetch_recent_positions,
    fetch_recent_tactics,
    fetch_version,
    get_connection,
    init_schema,
    insert_positions,
    insert_tactic_outcomes,
    insert_tactics,
    update_metrics_summary,
    upsert_raw_pgns,
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
from tactix.tactics_analyzer import analyze_positions

logger = get_logger(__name__)


def run_daily_game_sync(
    settings: Settings | None = None, source: str | None = None
) -> dict[str, object]:
    settings = settings or get_settings(source=source)
    if source:
        settings.source = source
    settings.apply_source_defaults()
    settings.ensure_dirs()

    since_ms = read_checkpoint(settings.checkpoint_path)
    if settings.source == "chesscom":
        games = fetch_chesscom_games(settings, since_ms)
    else:
        games = fetch_lichess_games(settings, since_ms)

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
            "checkpoint_ms": since_ms,
            "since_ms": since_ms,
        }

    upsert_raw_pgns(conn, games)

    if games:
        new_since = max(since_ms, latest_timestamp(games))
        write_checkpoint(settings.checkpoint_path, new_since)

    positions = []
    for game in games:
        positions.extend(
            extract_positions(
                game["pgn"], settings.user, settings.source, game_id=game["game_id"]
            )
        )

    position_ids = insert_positions(conn, positions)
    for pos, pos_id in zip(positions, position_ids, strict=False):
        pos["position_id"] = pos_id

    tactics_rows, outcomes_rows = analyze_positions(positions, settings)
    tactic_ids = insert_tactics(conn, tactics_rows)

    for row, tactic_id in zip(outcomes_rows, tactic_ids, strict=False):
        row["tactic_id"] = tactic_id

    insert_tactic_outcomes(conn, outcomes_rows)
    update_metrics_summary(conn)
    metrics_version = write_metrics_version(conn)
    settings.metrics_version_file.write_text(str(metrics_version))

    return {
        "source": settings.source,
        "user": settings.user,
        "fetched_games": len(games),
        "positions": len(positions),
        "tactics": len(tactics_rows),
        "metrics_version": metrics_version,
        "checkpoint_ms": read_checkpoint(settings.checkpoint_path),
        "since_ms": since_ms,
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
