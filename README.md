# TACTIX

TACTIX is a personal chess tactics intelligence and training platform. It ingests games from chess.com and lichess, analyzes user-to-move positions for hanging pieces and mate in 1/2, and produces a practice queue plus dashboard insights.

## Repository Structure (MVP)
- src/tactix: server-side Python package
- client: React dashboard
- data: local datasets and checkpoints
- tests: automated tests

## Quick Start

### Backend
1. Create a Python virtual environment.
2. Install dependencies from pyproject.toml.
3. Run the API server (FastAPI) via the existing project entrypoints.

### Frontend
1. cd client
2. npm install
3. npm run dev

### Tests
- Run backend tests with pytest.
- Run client tests with the client test script.

## Notes
- The MVP focuses on high-precision detection of hanging pieces and mate in 1/2.
- The canonical verification scenario is the 2026-02-01 chess.com bullet dataset.
