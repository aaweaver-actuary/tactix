from pathlib import Path


def test_repository_modules_do_not_import_fastapi() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    repo_paths = [
        "src/tactix/db/duckdb_dashboard_repository.py",
        "src/tactix/db/duckdb_metrics_repository.py",
        "src/tactix/db/duckdb_position_repository.py",
        "src/tactix/db/duckdb_raw_pgn_repository.py",
        "src/tactix/db/duckdb_tactic_repository.py",
        "src/tactix/db/postgres_analysis_repository.py",
        "src/tactix/db/postgres_ops_repository.py",
        "src/tactix/db/postgres_raw_pgn_repository.py",
    ]
    for rel_path in repo_paths:
        content = (repo_root / rel_path).read_text(encoding="utf-8")
        assert "fastapi" not in content.lower()
