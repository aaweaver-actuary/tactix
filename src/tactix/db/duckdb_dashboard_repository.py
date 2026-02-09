"""Dashboard query repository for DuckDB-backed storage."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from io import StringIO

import chess.pgn
import duckdb

from tactix._get_game_result_for_user_from_pgn_headers import (
    _get_game_result_for_user_from_pgn_headers,
)
from tactix.dashboard_query import DashboardQuery, resolve_dashboard_query
from tactix.db._append_date_range_filters import _append_date_range_filters
from tactix.db._append_optional_filter import _append_optional_filter
from tactix.db._append_time_control_filter import _append_time_control_filter
from tactix.db._normalize_filter import _normalize_filter
from tactix.db._rating_bucket_clause import _rating_bucket_clause
from tactix.db._rows_to_dicts import _rows_to_dicts
from tactix.db.raw_pgns_queries import latest_raw_pgns_query
from tactix.extract_pgn_metadata import extract_pgn_metadata
from tactix.tactic_scope import allowed_motif_list, is_allowed_motif_filter


@dataclass(frozen=True)
class DashboardFilterHelpers:
    """Filtering helpers for dashboard queries."""

    append_optional_filter: Callable[[list[str], list[object], str, object | None], None]
    append_date_range_filters: Callable[
        [list[str], list[object], object | None, object | None, str], None
    ]
    append_time_control_filter: Callable[[list[str], list[object], object | None, str], None]
    normalize_filter: Callable[[str | None], str | None]


@dataclass(frozen=True)
class DashboardQueryBuilders:
    """Query builders for dashboard reads."""

    build_games_filtered_query: Callable[[DashboardQuery], tuple[str, list[object]]]
    build_recent_games_query: Callable[[int, DashboardQuery], tuple[str, list[object]]]
    build_recent_tactics_query: Callable[[int, DashboardQuery], tuple[str, list[object]]]
    latest_raw_pgns_query: Callable[[], str]
    rating_bucket_clause: Callable[[str], str]


@dataclass(frozen=True)
class DuckDbDashboardRepositoryDependencies:
    """Dependencies used by the dashboard repository."""

    resolve_query: Callable[..., DashboardQuery]
    rows_to_dicts: Callable[[duckdb.DuckDBPyRelation], list[dict[str, object]]]
    filters: DashboardFilterHelpers
    builders: DashboardQueryBuilders
    format_recent_game_row: Callable[[Mapping[str, object], str | None], dict[str, object]]


class DuckDbDashboardRepository:
    """Encapsulates dashboard queries for DuckDB."""

    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        *,
        dependencies: DuckDbDashboardRepositoryDependencies,
    ) -> None:
        self._conn = conn
        self._dependencies = dependencies

    def _build_games_filtered_sql(
        self,
        query: DashboardQuery | str | None,
        *,
        filters: DashboardQuery | None,
        legacy: dict[str, object],
    ) -> tuple[str, list[object]]:
        deps = self._dependencies
        resolved = deps.resolve_query(query, filters=filters, **legacy)
        return deps.builders.build_games_filtered_query(resolved)

    def fetch_pipeline_table_counts(
        self,
        query: DashboardQuery | str | None = None,
        *,
        filters: DashboardQuery | None = None,
        **legacy: object,
    ) -> dict[str, int]:
        sql, params = self._build_games_filtered_sql(
            query,
            filters=filters,
            legacy=legacy,
        )
        return _fetch_pipeline_table_counts(self._conn, sql, params)

    def fetch_opportunity_motif_counts(
        self,
        query: DashboardQuery | str | None = None,
        *,
        filters: DashboardQuery | None = None,
        **legacy: object,
    ) -> dict[str, int]:
        sql, params = self._build_games_filtered_sql(
            query,
            filters=filters,
            legacy=legacy,
        )
        return _fetch_opportunity_motif_counts(self._conn, self._dependencies, sql, params)

    def fetch_metrics(  # noqa: PLR0915
        self,
        query: DashboardQuery | str | None = None,
        *,
        filters: DashboardQuery | None = None,
        **legacy: object,
    ) -> list[dict[str, object]]:
        deps = self._dependencies
        resolved = deps.resolve_query(query, filters=filters, **legacy)
        normalized_motif = deps.filters.normalize_filter(resolved.motif)
        if normalized_motif and not is_allowed_motif_filter(normalized_motif):
            return []
        sql, params = _build_metrics_query(deps, resolved, normalized_motif)
        result = self._conn.execute(sql, params)
        return deps.rows_to_dicts(result)

    def fetch_recent_games(
        self,
        query: DashboardQuery | str | None = None,
        *,
        limit: int = 20,
        user: str | None = None,
        **legacy: object,
    ) -> list[dict[str, object]]:
        deps = self._dependencies
        resolved = deps.resolve_query(query, **legacy)
        final_query, params = deps.builders.build_recent_games_query(limit, resolved)
        rows = deps.rows_to_dicts(self._conn.execute(final_query, params))
        return [deps.format_recent_game_row(row, user) for row in rows]

    def fetch_recent_positions(
        self,
        query: DashboardQuery | str | None = None,
        *,
        limit: int = 20,
        **legacy: object,
    ) -> list[dict[str, object]]:
        deps = self._dependencies
        resolved = deps.resolve_query(query, **legacy)
        normalized_rating = deps.filters.normalize_filter(resolved.rating_bucket)
        sql = f"""
            WITH latest_pgns AS (
                {deps.builders.latest_raw_pgns_query()}
            )
            SELECT p.*
            FROM positions p
            LEFT JOIN latest_pgns r ON r.game_id = p.game_id AND r.source = p.source
        """
        params: list[object] = []
        conditions: list[str] = []
        if resolved.source:
            conditions.append("p.source = ?")
            params.append(resolved.source)
        deps.filters.append_time_control_filter(
            conditions,
            params,
            resolved.time_control,
            "r.time_control",
        )
        if normalized_rating:
            conditions.append(deps.builders.rating_bucket_clause(normalized_rating))
        deps.filters.append_date_range_filters(
            conditions,
            params,
            resolved.start_date,
            resolved.end_date,
            "p.created_at",
        )
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY p.created_at DESC LIMIT ?"
        params.append(limit)
        result = self._conn.execute(sql, params)
        return deps.rows_to_dicts(result)

    def fetch_recent_tactics(
        self,
        query: DashboardQuery | str | None = None,
        *,
        limit: int = 20,
        **legacy: object,
    ) -> list[dict[str, object]]:
        deps = self._dependencies
        resolved = deps.resolve_query(query, **legacy)
        sql, params = deps.builders.build_recent_tactics_query(limit, resolved)
        return deps.rows_to_dicts(self._conn.execute(sql, params))


def _fetch_pipeline_table_counts(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
    params: list[object],
) -> dict[str, int]:
    motif_clause, motif_params = _scoped_motif_clause("o")
    conversion_clause, conversion_params = _scoped_motif_clause("c")
    practice_clause, practice_params = _scoped_motif_clause("q")
    sql += f"""
        SELECT
            (SELECT COUNT(*) FROM games_filtered) AS games,
            (
                SELECT COUNT(*)
                FROM positions p
                {_games_filtered_join_clause("p")}
                WHERE COALESCE(p.user_to_move, TRUE) = TRUE
            ) AS positions,
            (
                SELECT COUNT(*)
                FROM user_moves u
                {_games_filtered_join_clause("u")}
            ) AS user_moves,
            (
                SELECT COUNT(*)
                {_opportunities_from_games_filtered()}
                WHERE {motif_clause}
            ) AS opportunities,
            (
                SELECT COUNT(*)
                FROM conversions c
                {_games_filtered_join_clause("c")}
                WHERE {conversion_clause}
            ) AS conversions,
            (
                SELECT COUNT(*)
                FROM practice_queue q
                {_games_filtered_join_clause("q")}
                WHERE {practice_clause}
            ) AS practice_queue
    """
    params.extend(motif_params)
    params.extend(conversion_params)
    params.extend(practice_params)
    result = conn.execute(sql, params)
    row = result.fetchone()
    if not row:
        return {
            "games": 0,
            "positions": 0,
            "user_moves": 0,
            "opportunities": 0,
            "conversions": 0,
            "practice_queue": 0,
        }
    columns = [desc[0] for desc in result.description]
    return {column: int(value or 0) for column, value in zip(columns, row, strict=False)}


def _fetch_opportunity_motif_counts(
    conn: duckdb.DuckDBPyConnection,
    deps: DuckDbDashboardRepositoryDependencies,
    sql: str,
    params: list[object],
) -> dict[str, int]:
    motif_clause, motif_params = _scoped_motif_clause("o")
    sql += f"""
        SELECT o.motif, COUNT(*) AS total
        {_opportunities_from_games_filtered()}
        WHERE {motif_clause}
        GROUP BY o.motif
        ORDER BY o.motif
    """
    params.extend(motif_params)
    rows = deps.rows_to_dicts(conn.execute(sql, params))
    return {str(row.get("motif")): int(row.get("total") or 0) for row in rows}


def _build_games_filtered_query(resolved: DashboardQuery) -> tuple[str, list[object]]:
    sql = """
        WITH games_filtered AS (
            SELECT *
            FROM games r
    """
    params: list[object] = []
    conditions: list[str] = []
    if resolved.source:
        conditions.append("r.source = ?")
        params.append(resolved.source)
    _append_game_query_filters(
        conditions,
        params,
        resolved,
        timestamp_expr="to_timestamp(r.last_timestamp_ms / 1000)",
    )
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += """
        )
    """
    return sql, params


def _games_filtered_join_clause(alias: str) -> str:
    return (
        "INNER JOIN games_filtered r\n"
        f"                ON {alias}.game_id = r.game_id"
        f" AND {alias}.source = r.source"
    )


def _opportunities_from_games_filtered() -> str:
    return "FROM opportunities o\n" + _games_filtered_join_clause("o")


def _build_metrics_query(
    deps: DuckDbDashboardRepositoryDependencies,
    resolved: DashboardQuery,
    normalized_motif: str | None,
) -> tuple[str, list[object]]:
    sql = "SELECT * FROM metrics_summary"
    params: list[object] = []
    conditions: list[str] = []
    if resolved.source:
        conditions.append("source = ?")
        params.append(resolved.source)
    deps.filters.append_optional_filter(conditions, params, "motif = ?", normalized_motif)
    deps.filters.append_optional_filter(
        conditions, params, "rating_bucket = ?", resolved.rating_bucket
    )
    deps.filters.append_optional_filter(
        conditions,
        params,
        "time_control = ?",
        resolved.time_control,
    )
    if normalized_motif is None:
        allowed = allowed_motif_list()
        placeholders = ", ".join(["?"] * len(allowed))
        conditions.append(f"(motif IN ({placeholders}) OR motif IS NULL)")
        params.extend(allowed)
    deps.filters.append_date_range_filters(
        conditions,
        params,
        resolved.start_date,
        resolved.end_date,
        "trend_date",
    )
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    return sql, params


def _scoped_motif_clause(alias: str) -> tuple[str, list[object]]:
    allowed = allowed_motif_list()
    placeholders = ", ".join(["?"] * len(allowed))
    clause = (
        f"{alias}.motif IN ({placeholders})"
        f" AND ({alias}.motif != 'mate' OR {alias}.mate_type IS NOT NULL)"
    )
    return clause, list(allowed)


def _append_game_query_filters(
    conditions: list[str],
    params: list[object],
    query: DashboardQuery,
    *,
    timestamp_expr: str,
) -> None:
    _append_time_control_filter(conditions, params, query.time_control, "r.time_control")
    normalized_rating = _normalize_filter(query.rating_bucket)
    if normalized_rating:
        conditions.append(_rating_bucket_clause(normalized_rating))
    _append_date_range_filters(
        conditions,
        params,
        query.start_date,
        query.end_date,
        timestamp_expr,
    )


def _build_recent_games_query(limit: int, query: DashboardQuery) -> tuple[str, list[object]]:
    sql = f"""
        WITH latest_pgns AS (
            {latest_raw_pgns_query()}
        ),
        filtered AS (
            SELECT
                r.game_id,
                r.source,
                r.user,
                r.pgn,
                r.time_control,
                r.user_rating,
                r.last_timestamp_ms
            FROM latest_pgns r
    """
    params: list[object] = []
    conditions: list[str] = []
    _append_game_query_filters(
        conditions,
        params,
        query,
        timestamp_expr="to_timestamp(r.last_timestamp_ms / 1000)",
    )
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += "\n        )\n    "
    if query.source:
        params.append(query.source)
        final_query = (
            sql
            + "SELECT * FROM filtered WHERE source = ? "
            + "ORDER BY last_timestamp_ms DESC, game_id LIMIT ?"
        )
        params.append(limit)
        return final_query, params
    final_query = (
        sql
        + """
        , ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY source
                    ORDER BY last_timestamp_ms DESC
                ) AS source_rank
            FROM filtered
        )
        SELECT * EXCLUDE (source_rank)
        FROM ranked
        WHERE source_rank <= ?
        ORDER BY last_timestamp_ms DESC, game_id
        """
    )
    params.append(limit)
    return final_query, params


def _build_recent_tactics_query(limit: int, query: DashboardQuery) -> tuple[str, list[object]]:
    normalized_motif = _normalize_filter(query.motif)
    normalized_rating = _normalize_filter(query.rating_bucket)
    sql = f"""
        WITH latest_pgns AS (
            {latest_raw_pgns_query()}
        )
        SELECT t.*, o.result, o.eval_delta, o.user_uci, p.source
        FROM tactics t
        LEFT JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
        LEFT JOIN positions p ON p.position_id = t.position_id
        LEFT JOIN latest_pgns r ON r.game_id = p.game_id AND r.source = p.source
    """
    params: list[object] = []
    conditions: list[str] = []
    _append_recent_tactics_filters(
        conditions,
        params,
        query,
        normalized_motif,
        normalized_rating,
    )
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY t.created_at DESC LIMIT ?"
    params.append(limit)
    return sql, params


def _append_recent_tactics_filters(
    conditions: list[str],
    params: list[object],
    query: DashboardQuery,
    normalized_motif: str | None,
    normalized_rating: str | None,
) -> None:
    _append_optional_filter(conditions, params, "p.source = ?", query.source)
    if not _append_scoped_tactics_motif_filters(conditions, params, normalized_motif):
        return
    _append_time_control_filter(conditions, params, query.time_control, "r.time_control")
    if normalized_rating:
        conditions.append(_rating_bucket_clause(normalized_rating))
    _append_date_range_filters(
        conditions,
        params,
        query.start_date,
        query.end_date,
        "t.created_at",
    )


def _append_scoped_tactics_motif_filters(
    conditions: list[str],
    params: list[object],
    normalized_motif: str | None,
) -> bool:
    if normalized_motif and not is_allowed_motif_filter(normalized_motif):
        conditions.append("1 = 0")
        return False
    _append_optional_filter(conditions, params, "t.motif = ?", normalized_motif)
    if normalized_motif == "mate":
        conditions.append("t.mate_type IS NOT NULL")
    if normalized_motif is None:
        allowed = allowed_motif_list()
        placeholders = ", ".join(["?"] * len(allowed))
        conditions.append(f"t.motif IN ({placeholders})")
        params.extend(allowed)
        conditions.append("(t.motif != 'mate' OR t.mate_type IS NOT NULL)")
    return True


def _resolve_recent_game_user(row: Mapping[str, object], user: str | None) -> str:
    return user or str(row.get("user") or "")


def _normalize_player_name(value: object | None) -> str:
    return str(value or "").lower()


def _is_user_player(player: str, user_lower: str) -> bool:
    return bool(player) and player == user_lower


def _fallback_opponent(white: object | None, black: object | None) -> object | None:
    return black or white


def _resolve_opponent_and_color(
    user_lower: str,
    white: object | None,
    black: object | None,
) -> tuple[object | None, str | None]:
    white_lower = _normalize_player_name(white)
    black_lower = _normalize_player_name(black)
    if _is_user_player(white_lower, user_lower):
        return black, "white"
    if _is_user_player(black_lower, user_lower):
        return white, "black"
    return _fallback_opponent(white, black), None


def _timestamp_ms_to_iso(value: object) -> str | None:
    if isinstance(value, (int, float)) and int(value) > 0:
        return datetime.fromtimestamp(int(value) / 1000, tz=UTC).isoformat()
    return None


def _resolve_played_at(
    metadata: Mapping[str, object],
    row: Mapping[str, object],
) -> str | None:
    played_at = _timestamp_ms_to_iso(metadata.get("start_timestamp_ms"))
    if played_at:
        return played_at
    return _timestamp_ms_to_iso(row.get("last_timestamp_ms"))


def _resolve_recent_game_result(
    pgn_text: str,
    user: str,
    fallback: object,
) -> object:
    if not pgn_text.strip().startswith("["):
        return fallback
    try:
        headers = chess.pgn.read_headers(StringIO(pgn_text))
        if headers is None:
            return fallback
        return str(_get_game_result_for_user_from_pgn_headers(headers, user))
    except (ValueError, TypeError):
        return fallback


def _recent_game_payload(
    row: Mapping[str, object],
    metadata: Mapping[str, object],
    opponent: object | None,
    user_color: str | None,
    played_at: str | None,
) -> dict[str, object]:
    return {
        "game_id": str(row.get("game_id") or ""),
        "source": row.get("source"),
        "opponent": opponent,
        "result": metadata.get("result"),
        "played_at": played_at,
        "time_control": metadata.get("time_control") or row.get("time_control") or None,
        "user_color": user_color,
    }


def _format_recent_game_row(row: Mapping[str, object], user: str | None) -> dict[str, object]:
    raw_user = _resolve_recent_game_user(row, user)
    pgn_text = str(row.get("pgn") or "")
    metadata = extract_pgn_metadata(pgn_text, raw_user)
    opponent, user_color = _resolve_opponent_and_color(
        raw_user.lower(),
        metadata.get("white_player"),
        metadata.get("black_player"),
    )
    played_at = _resolve_played_at(metadata, row)
    result = _resolve_recent_game_result(pgn_text, raw_user, metadata.get("result"))
    return _recent_game_payload(
        row,
        {**metadata, "result": result},
        opponent,
        user_color,
        played_at,
    )


def default_dashboard_repository_dependencies() -> DuckDbDashboardRepositoryDependencies:
    filters = DashboardFilterHelpers(
        append_optional_filter=_append_optional_filter,
        append_date_range_filters=_append_date_range_filters,
        append_time_control_filter=_append_time_control_filter,
        normalize_filter=_normalize_filter,
    )
    builders = DashboardQueryBuilders(
        build_games_filtered_query=_build_games_filtered_query,
        build_recent_games_query=_build_recent_games_query,
        build_recent_tactics_query=_build_recent_tactics_query,
        latest_raw_pgns_query=latest_raw_pgns_query,
        rating_bucket_clause=_rating_bucket_clause,
    )
    return DuckDbDashboardRepositoryDependencies(
        resolve_query=resolve_dashboard_query,
        rows_to_dicts=_rows_to_dicts,
        filters=filters,
        builders=builders,
        format_recent_game_row=_format_recent_game_row,
    )
