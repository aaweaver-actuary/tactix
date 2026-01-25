# TACTIX project summary

Purpose: Personal chess tactics intelligence platform that ingests Lichess/Chess.com games, extracts positions where the user moves, analyzes tactics with Stockfish, stores results in DuckDB/Parquet, and serves analytics + practice via FastAPI and a React/Vite dashboard. Airflow orchestrates ingestion/extraction/analysis/metrics.

Architecture highlights:
- Layered design: core primitives → domain services → adapters/integrations (no mixing of concerns).
- Rust for PGN parsing/position extraction; Python for orchestration/analysis; React for UI.
- Data stored in DuckDB; metrics and practice endpoints via FastAPI; SSE for job progress.
