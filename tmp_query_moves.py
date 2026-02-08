from tactix.db.duckdb_store import get_connection

def main():
    conn = get_connection('/Users/andy/tactix/tmpxyyemft3/tactix_feature_pipeline_validation_2026_02_01.duckdb')
    moves = ['c8e6', 'f6e5']
    for mv in moves:
        rows = conn.execute(
            "SELECT t.tactic_id, t.motif, o.result FROM tactics t JOIN positions p ON p.position_id = t.position_id JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id WHERE p.uci = ?",
            [mv],
        ).fetchall()
        print(mv, rows)
    conn.close()

if __name__ == '__main__':
    main()
