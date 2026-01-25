## TACTIX — Personal Chess Tactics Intelligence

### What this is
- Batch-first pipeline that ingests your games from Lichess and Chess.com, extracts positions where you had to move, runs Stockfish to find tactical motifs, stores results in DuckDB/Parquet, and serves analytics + practice via FastAPI and a React/Vite dashboard.
- Airflow DAGs orchestrate ingestion, extraction, analysis, and metric refresh. Practice mode drills missed tactics pulled from your own games.

### Prereqs
- macOS or Linux with `uv` (Python 3.13+), `node`/`npm` (for Vite), `cargo`/Rust toolchain (for the PGN→FEN extractor via maturin), and optional `duckdb` CLI for inspection.

### Quick start
1) Make the helper executable: `chmod +x ./init.sh`
2) Install deps (Python, JS, optional Airflow bootstrap, Rust build if present): `./init.sh`
3) To auto-start dev servers (when app code exists): `START_SERVERS=1 ./init.sh`

### Docker (recommended for consistent local setup)
From the repo root:

1) Build and start all services:
	- `docker compose -f docker/compose.yml up --build -d`
2) Check service health:
	- API: `curl -s http://localhost:8000/api/health`
	- Dashboard: http://localhost:5173
	- Airflow UI: http://localhost:8080

Notes:
- Airflow may take ~1–2 minutes to become available on first boot.
- The stack uses the `tactix-net` bridge network. The containers expose ports 8000 (API), 5173 (UI), and 8080 (Airflow).
- Data persists via the `data/` volume mounted into containers.

To stop the stack:
- `docker compose -f docker/compose.yml down`

### Services (once implemented)
- FastAPI: http://localhost:8000 (SSE for job streams, analytics/practice APIs)
- React/Vite dashboard: http://localhost:5173
- Airflow UI: http://localhost:8080

### Next steps for contributors
- Keep feature coverage aligned with `feature_list.json` (do not remove or edit entries; only flip `passes` to true when verified).
- Add Python deps with `uv add <package>`; run `uv sync` to update the venv.
- For Rust extractor, place the crate under `src/` and build with `cargo build --release` (or `uv run maturin develop`).
