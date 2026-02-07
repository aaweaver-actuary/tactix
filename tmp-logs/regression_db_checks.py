import argparse
import json
from pathlib import Path

import duckdb


def run_checks(db_path: Path, source: str, start_date: str, end_date: str) -> dict:
    con = duckdb.connect(str(db_path))
    opportunity_cols = [row[1] for row in con.execute("pragma table_info('opportunities')").fetchall()]
    if 'type' in opportunity_cols:
        type_col = 'type'
    elif 'motif' in opportunity_cols:
        type_col = 'motif'
    else:
        type_col = None

    scoped_games = """
        select game_id
        from games
        where source = ?
          and cast(played_at as date) between ? and ?
    """

    games_count = con.execute(
        f"select count(*) from ({scoped_games})",
        [source, start_date, end_date],
    ).fetchone()[0]
    positions_count = con.execute(
        f"""
        select count(*)
        from positions
        where user_to_move = true
          and game_id in ({scoped_games})
        """,
        [source, start_date, end_date],
    ).fetchone()[0]
    user_moves_count = con.execute(
        f"""
        select count(*)
        from user_moves
        where position_id in (
            select position_id
            from positions
            where game_id in ({scoped_games})
        )
        """,
        [source, start_date, end_date],
    ).fetchone()[0]

    opportunities_count = con.execute(
        f"""
        select count(*)
        from opportunities
        where position_id in (
            select position_id
            from positions
            where game_id in ({scoped_games})
        )
        """,
        [source, start_date, end_date],
    ).fetchone()[0]

    opportunity_type_counts = {}
    if type_col:
        rows = con.execute(
            f"""
            select {type_col}, count(*)
            from opportunities
            where position_id in (
                select position_id
                from positions
                where game_id in ({scoped_games})
            )
            group by {type_col}
            order by {type_col}
            """,
            [source, start_date, end_date],
        ).fetchall()
        opportunity_type_counts = {row[0]: row[1] for row in rows}

    conversions_count = con.execute(
        f"""
        select count(*)
        from conversions
        where opportunity_id in (
            select opportunity_id
            from opportunities
            where position_id in (
                select position_id
                from positions
                where game_id in ({scoped_games})
            )
        )
        """,
        [source, start_date, end_date],
    ).fetchone()[0]

    conversion_result_rows = con.execute(
        f"""
        select result, count(*)
        from conversions
        where opportunity_id in (
            select opportunity_id
            from opportunities
            where position_id in (
                select position_id
                from positions
                where game_id in ({scoped_games})
            )
        )
        group by result
        order by result
        """,
        [source, start_date, end_date],
    ).fetchall()
    conversion_result_counts = {row[0]: row[1] for row in conversion_result_rows}
    conversions_found = conversion_result_counts.get('found', 0)
    conversions_missed = conversion_result_counts.get('missed', 0)

    practice_queue_count = con.execute(
        f"""
        select count(*)
        from practice_queue
        where game_id in ({scoped_games})
        """,
        [source, start_date, end_date],
    ).fetchone()[0]

    return {
        'db_path': str(db_path),
        'source': source,
        'start_date': start_date,
        'end_date': end_date,
        'games': games_count,
        'positions_user_to_move': positions_count,
        'user_moves': user_moves_count,
        'opportunities': opportunities_count,
        'opportunity_type_counts': opportunity_type_counts,
        'conversions': conversions_count,
        'conversion_result_counts': conversion_result_counts,
        'conversions_found': conversions_found,
        'conversions_missed': conversions_missed,
        'practice_queue': practice_queue_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--db-path', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--start-date', required=True)
    parser.add_argument('--end-date', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    result = run_checks(Path(args.db_path), args.source, args.start_date, args.end_date)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
