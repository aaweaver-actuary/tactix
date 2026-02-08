from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timezone
from functools import lru_cache
from io import StringIO
from pathlib import Path

import chess
import chess.pgn
import pytest

from tactix.BaseTacticDetector import BaseTacticDetector
from tactix._get_game_result_for_user_from_pgn_headers import (
    _get_game_result_for_user_from_pgn_headers,
)
from tactix._get_user_color_from_pgn_headers import _get_user_color_from_pgn_headers
from tactix.define_base_db_store__db_store import BaseDbStore
from tactix.config import Settings
from tactix.init_analysis_schema import init_analysis_schema
from tactix.pgn_utils import extract_game_id, split_pgn_chunks
from tactix.postgres_connection import postgres_connection
from tactix.postgres_enabled import postgres_enabled
from tactix.init_pgn_schema import (
    init_pgn_schema,
)
from tactix.normalize_pgn import normalize_pgn

USER = "groborger"
SOURCE = "chesscom"
FIXTURE_DATE = date(2026, 2, 1)
FIXTURE_DATE_TEXT = "2026-02-01"
TIME_CONTROL = "120+1"
BULLET_TIME_CONTROL_SQL = "split_part(time_control, '+', 1)::int <= 180"
OUTCOME_CASE_SQL = """
CASE
    WHEN player_username = white_player AND result = '1-0' THEN 'win'
    WHEN player_username = black_player AND result = '0-1' THEN 'win'
    WHEN player_username = white_player AND result = '0-1' THEN 'loss'
    WHEN player_username = black_player AND result = '1-0' THEN 'loss'
    ELSE 'draw'
END
"""


def _fixture_game_filter_sql() -> str:
    return f"""
    WHERE source = %s
      AND utc_date = %s
      AND {BULLET_TIME_CONTROL_SQL}
      AND game_id = ANY(%s)
      AND pgn_hash = ANY(%s)
    """


def _fixture_query_args() -> tuple[str, str, list[str], list[str]]:
    return (
        SOURCE,
        FIXTURE_DATE_TEXT,
        list(_fixture_game_ids()),
        list(_fixture_pgn_hashes()),
    )


@dataclass(frozen=True)
class HangingPosition:
    position_id: int
    piece_label: str
    fen: str
    move_number: int
    ply: int
    side_to_move: str
    uci: str
    san: str
    capture_uci: str | None
    capture_san: str | None
    capture_square: str | None


@dataclass(frozen=True)
class FixtureContext:
    loss_game_id: str
    blunder_move_number: int
    hanging_primary: HangingPosition
    hanging_secondary: HangingPosition


def _fixture_path() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "chesscom_2_bullet_games.pgn"


def _load_fixture_games() -> list[chess.pgn.Game]:
    games: list[chess.pgn.Game] = []
    for chunk in split_pgn_chunks(_fixture_path().read_text()):
        game = chess.pgn.read_game(StringIO(chunk))
        if game:
            games.append(game)
    if len(games) != 2:
        raise AssertionError(f"Expected 2 fixture games, found {len(games)}")
    return games


def _normalize_date(header_value: str | None) -> str:
    if not header_value:
        return FIXTURE_DATE_TEXT
    try:
        parsed = datetime.strptime(header_value, "%Y.%m.%d").replace(tzinfo=UTC)
        return parsed.date().isoformat()
    except ValueError:
        return FIXTURE_DATE_TEXT


def _piece_label(piece_type: chess.PieceType) -> str:
    if piece_type == chess.BISHOP:
        return "bishop"
    if piece_type == chess.KNIGHT:
        return "knight"
    if piece_type == chess.ROOK:
        return "rook"
    if piece_type == chess.QUEEN:
        return "queen"
    return "pawn"


def _is_hanging_piece(board: chess.Board, square: chess.Square, mover_color: bool) -> bool:
    piece = board.piece_at(square)
    if not piece or piece.color != mover_color:
        return False
    if piece.piece_type not in {chess.BISHOP, chess.KNIGHT, chess.ROOK, chess.QUEEN}:
        return False
    opponent = not mover_color
    if not any(
        not board.is_pinned(opponent, attacker) for attacker in board.attackers(opponent, square)
    ):
        return False
    return not any(
        not board.is_pinned(mover_color, defender)
        for defender in board.attackers(mover_color, square)
    )


def _find_blunder_move_number(game: chess.pgn.Game, user_color: bool) -> int:
    board = game.board()
    last_move_number: int | None = None
    for node in game.mainline():
        move = node.move
        if move is None:
            continue
        if board.turn == user_color:
            last_move_number = board.fullmove_number
        board.push(move)
    if last_move_number is None:
        raise AssertionError("No user move found for fixture game")
    return last_move_number + 1


def _capture_square(board: chess.Board, move: chess.Move) -> chess.Square:
    if board.is_en_passant(move):
        return move.to_square + (-8 if board.turn == chess.WHITE else 8)
    return move.to_square


def _hanging_user_piece_labels_after_move(fen: str, user_move_uci: str) -> set[str]:  # noqa: PLR0912
    if not user_move_uci:
        return set()
    board = chess.Board(fen)
    move = chess.Move.from_uci(user_move_uci)
    if move not in board.legal_moves:
        return set()
    moved_piece = board.piece_at(move.from_square)
    user_color = board.turn
    board.push(move)
    if moved_piece is None:
        return set()
    target_square = move.to_square
    labels: set[str] = set()
    if board.is_attacked_by(not user_color, target_square):
        is_unprotected = not board.is_attacked_by(user_color, target_square)
        is_favorable = False
        for response in board.legal_moves:
            if not board.is_capture(response):
                continue
            capture_square = _capture_square(board, response)
            if capture_square != target_square:
                continue
            mover_piece = board.piece_at(response.from_square)
            if mover_piece is None:
                continue
            is_favorable = BaseTacticDetector.piece_value(
                moved_piece.piece_type
            ) > BaseTacticDetector.piece_value(mover_piece.piece_type)
            if is_favorable:
                break
        if is_unprotected or is_favorable:
            if moved_piece.piece_type == chess.KNIGHT:
                labels.add("knight")
            elif moved_piece.piece_type == chess.BISHOP:
                labels.add("bishop")
    return labels


def _find_hanging_positions(
    game: chess.pgn.Game,
    user_color: bool,
    blunder_move_number: int,
) -> tuple[HangingPosition, HangingPosition]:
    board = game.board()
    hanging_positions: list[HangingPosition] = []
    seen_labels: set[str] = set()
    position_id = 6001

    for node in game.mainline():
        move = node.move
        if move is None:
            continue
        if board.turn == user_color:
            move_number = board.fullmove_number
            if move_number >= blunder_move_number:
                break
            fen = board.fen()
            ply = board.ply()
            san = board.san(move)
            uci = move.uci()
            side_to_move = "white" if board.turn == chess.WHITE else "black"

            def _capture_for(square: chess.Square) -> tuple[str | None, str | None]:
                for candidate in board.legal_moves:
                    if candidate.to_square == square:
                        return candidate.uci(), board.san(candidate)
                return None, None

            labels = _hanging_user_piece_labels_after_move(fen, uci)
            for piece_label in sorted(labels):
                if piece_label not in {"bishop", "knight"}:
                    continue
                if piece_label in seen_labels:
                    continue
                capture_uci, capture_san = _capture_for(move.to_square)
                hanging_positions.append(
                    HangingPosition(
                        position_id=position_id,
                        piece_label=piece_label,
                        fen=fen,
                        move_number=move_number,
                        ply=ply,
                        side_to_move=side_to_move,
                        uci=uci,
                        san=san,
                        capture_uci=capture_uci,
                        capture_san=capture_san,
                        capture_square=chess.square_name(move.to_square),
                    )
                )
                seen_labels.add(piece_label)
                position_id += 1
                if len(hanging_positions) >= 2:
                    break
            if len(hanging_positions) >= 2:
                break
        board.push(move)

    if len(hanging_positions) < 2:
        raise AssertionError("Fixture game did not expose two hanging pieces")
    return hanging_positions[0], hanging_positions[1]


@lru_cache
def _fixture_context() -> FixtureContext:
    games = _load_fixture_games()
    loss_game = next(
        game
        for game in games
        if _get_game_result_for_user_from_pgn_headers(game.headers, USER) == "loss"
    )
    loss_game_id = extract_game_id(str(loss_game))
    user_color = _get_user_color_from_pgn_headers(loss_game.headers, USER)
    user_color_value = user_color.value
    blunder_move_number = _find_blunder_move_number(loss_game, user_color_value)
    hanging_primary, hanging_secondary = _find_hanging_positions(
        loss_game,
        user_color_value,
        blunder_move_number,
    )
    return FixtureContext(
        loss_game_id=loss_game_id,
        blunder_move_number=blunder_move_number,
        hanging_primary=hanging_primary,
        hanging_secondary=hanging_secondary,
    )


@lru_cache
def _fixture_game_ids() -> tuple[str, str]:
    return tuple(extract_game_id(str(game)) for game in _load_fixture_games())


@lru_cache
def _fixture_pgn_hashes() -> tuple[str, str]:
    hashes: list[str] = []
    for game in _load_fixture_games():
        normalized = normalize_pgn(str(game))
        hashes.append(BaseDbStore.hash_pgn(normalized))
    return tuple(hashes)


def _ensure_fixture_seeded(conn) -> None:
    init_pgn_schema(conn)
    init_analysis_schema(conn)
    context = _fixture_context()
    games = _load_fixture_games()

    with conn.cursor() as cur:
        for game in games:
            headers = game.headers
            game_id = extract_game_id(str(game))
            pgn_text = str(game)
            normalized = normalize_pgn(pgn_text)
            pgn_hash = BaseDbStore.hash_pgn(normalized)
            user_color = _get_user_color_from_pgn_headers(headers, USER)
            user_color_value = user_color.value
            white_elo = int(headers.get("WhiteElo") or 0)
            black_elo = int(headers.get("BlackElo") or 0)
            user_rating = black_elo if user_color_value == chess.BLACK else white_elo
            utc_date = _normalize_date(headers.get("Date"))

            cur.execute(
                """
                INSERT INTO tactix_pgns.raw_pgns (
                    game_id,
                    source,
                    player_username,
                    pgn_raw,
                    pgn_normalized,
                    pgn_hash,
                    pgn_version,
                    user_rating,
                    time_control,
                    ingested_at,
                    white_player,
                    black_player,
                    white_elo,
                    black_elo,
                    result,
                    event,
                    site,
                    utc_date,
                    termination
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT DO NOTHING
                """,
                (
                    game_id,
                    SOURCE,
                    USER,
                    pgn_text,
                    normalized,
                    pgn_hash,
                    user_rating,
                    headers.get("TimeControl"),
                    datetime(2026, 2, 1, tzinfo=timezone.utc),
                    headers.get("White"),
                    headers.get("Black"),
                    white_elo,
                    black_elo,
                    headers.get("Result"),
                    headers.get("Event"),
                    headers.get("Site"),
                    utc_date,
                    headers.get("Termination"),
                ),
            )

        cur.execute(
            """
            DELETE FROM tactix_analysis.tactic_outcomes
            WHERE tactic_id IN (
                SELECT tactic_id
                FROM tactix_analysis.tactics
                WHERE position_id = %s OR position_id = %s
            )
            """,
            (context.hanging_primary.position_id, context.hanging_secondary.position_id),
        )
        cur.execute(
            """
            DELETE FROM tactix_analysis.tactics
            WHERE position_id = %s OR position_id = %s
            """,
            (context.hanging_primary.position_id, context.hanging_secondary.position_id),
        )
        cur.execute(
            """
            DELETE FROM tactix_analysis.positions
            WHERE position_id = %s OR position_id = %s
            """,
            (context.hanging_primary.position_id, context.hanging_secondary.position_id),
        )

        hanging_positions = [context.hanging_primary, context.hanging_secondary]
        for position in hanging_positions:
            cur.execute(
                """
                INSERT INTO tactix_analysis.positions (
                    position_id,
                    game_id,
                    source,
                    fen,
                    ply,
                    move_number,
                    side_to_move,
                    uci,
                    san,
                    clock_seconds,
                    is_legal,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, TRUE, %s)
                """,
                (
                    position.position_id,
                    context.loss_game_id,
                    SOURCE,
                    position.fen,
                    position.ply,
                    position.move_number,
                    position.side_to_move,
                    position.uci,
                    position.san,
                    datetime(2026, 2, 1, tzinfo=timezone.utc),
                ),
            )

        for position in hanging_positions:
            explanation = (
                f"hanging_piece tactic. Hung {position.piece_label}"
                f" on {position.capture_square or 'unknown'}"
            )
            cur.execute(
                """
                INSERT INTO tactix_analysis.tactics (
                    game_id,
                    position_id,
                    motif,
                    severity,
                    best_uci,
                    best_san,
                    explanation,
                    eval_cp,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING tactic_id
                """,
                (
                    context.loss_game_id,
                    position.position_id,
                    "hanging_piece",
                    1.0,
                    position.capture_uci or "",
                    position.capture_san,
                    explanation,
                    -150,
                    datetime(2026, 2, 1, tzinfo=timezone.utc),
                ),
            )
            tactic_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO tactix_analysis.tactic_outcomes (
                    tactic_id,
                    result,
                    user_uci,
                    eval_delta,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    tactic_id,
                    "missed",
                    position.uci,
                    -120,
                    datetime(2026, 2, 1, tzinfo=timezone.utc),
                ),
            )
    conn.commit()


@pytest.fixture(scope="module")
def pg_conn():
    settings = Settings()
    if not postgres_enabled(settings):
        pytest.skip("Postgres not configured")
    with postgres_connection(settings) as conn:
        if conn is None:
            pytest.skip("Postgres connection unavailable")
        _ensure_fixture_seeded(conn)
        yield conn


def test_exactly_two_bullet_games_ingested_for_2026_02_01(pg_conn):
    with pg_conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT COUNT(*)
            FROM tactix_pgns.raw_pgns
            {_fixture_game_filter_sql()}
            """,
            _fixture_query_args(),
        )
        count = cur.fetchone()[0]
    assert count == 2


def test_outcome_distribution_is_one_win_one_loss(pg_conn):
    with pg_conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT
                SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) AS wins,
                SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) AS losses
            FROM (
                SELECT
                    {OUTCOME_CASE_SQL} AS outcome
                FROM tactix_pgns.raw_pgns
                {_fixture_game_filter_sql()}
            ) AS outcomes
            """,
            _fixture_query_args(),
        )
        wins, losses = cur.fetchone()
    assert wins == 1
    assert losses == 1


def test_rating_deltas_match_expectations(pg_conn):
    with pg_conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT
                SUM(CASE WHEN outcome = 'loss' AND rating_delta > 50 THEN 1 ELSE 0 END) AS loss_gt_50,
                SUM(CASE WHEN outcome = 'win' AND rating_delta <= 50 THEN 1 ELSE 0 END) AS win_le_50,
                SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) AS losses,
                SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) AS wins
            FROM (
                SELECT
                    CASE
                        WHEN player_username = white_player THEN black_elo - white_elo
                        WHEN player_username = black_player THEN white_elo - black_elo
                        ELSE NULL
                    END AS rating_delta,
                    {OUTCOME_CASE_SQL} AS outcome
                FROM tactix_pgns.raw_pgns
                {_fixture_game_filter_sql()}
            ) AS ratings
            """,
            _fixture_query_args(),
        )
        loss_gt_50, win_le_50, losses, wins = cur.fetchone()
    assert losses == 1
    assert wins == 1
    assert loss_gt_50 == 1
    assert win_le_50 == 1


def test_at_least_two_practice_positions_for_2026_02_01(pg_conn):
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM tactix_analysis.positions p
            JOIN tactix_analysis.tactics t ON t.position_id = p.position_id
            JOIN tactix_analysis.tactic_outcomes o ON o.tactic_id = t.tactic_id
            WHERE p.created_at::date = %s
              AND o.result = 'missed'
            """,
            (FIXTURE_DATE_TEXT,),
        )
        count = cur.fetchone()[0]
    assert count >= 2


def test_positions_reference_loss_game_and_missed_before_blunder(pg_conn):
    context = _fixture_context()
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.position_id, p.game_id, p.move_number, o.result
            FROM tactix_analysis.positions p
            JOIN tactix_analysis.tactics t ON t.position_id = p.position_id
            JOIN tactix_analysis.tactic_outcomes o ON o.tactic_id = t.tactic_id
            WHERE p.game_id = %s
            ORDER BY p.move_number
            """,
            (context.loss_game_id,),
        )
        rows = cur.fetchall()
    assert len(rows) >= 2
    assert all(row[1] == context.loss_game_id for row in rows)
    assert all(row[3] == "missed" for row in rows)
    assert all(row[2] < context.blunder_move_number for row in rows)


def test_positions_include_hanging_piece_labels(pg_conn):
    context = _fixture_context()
    labels = {context.hanging_primary.piece_label, context.hanging_secondary.piece_label}
    assert labels == {"bishop", "knight"}
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT explanation
            FROM tactix_analysis.tactics
            WHERE game_id = %s
            """,
            (context.loss_game_id,),
        )
        explanations = [row[0] or "" for row in cur.fetchall()]
    normalized = [text.lower() for text in explanations]
    for label in labels:
        assert any(label in text for text in normalized)


def test_positions_include_game_id_move_number_and_fen(pg_conn):
    context = _fixture_context()
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM tactix_analysis.positions p
            JOIN tactix_analysis.tactics t ON t.position_id = p.position_id
            JOIN tactix_analysis.tactic_outcomes o ON o.tactic_id = t.tactic_id
            WHERE p.game_id = %s
              AND (p.game_id IS NULL OR p.move_number IS NULL OR p.fen IS NULL)
            """,
            (context.loss_game_id,),
        )
        missing = cur.fetchone()[0]
    assert missing == 0
