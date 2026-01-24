#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

info() { printf "[init] %s\n" "$*"; }
warn() { printf "[init][warn] %s\n" "$*"; }

info "Using uv virtual environment (expected at .venv)."
info "1) Installing Python dependencies via uv sync"
if command -v uv >/dev/null 2>&1; then
  uv sync
else
  warn "uv not found. Install uv from https://github.com/astral-sh/uv then re-run."
  exit 1
fi

info "2) Installing JavaScript dependencies (client/) if present"
if [ -f client/package.json ]; then
  (cd client && npm install)
else
  warn "client/package.json not found; skipping frontend install"
fi

info "3) Bootstrapping Airflow state (local metadata DB)"
export AIRFLOW_HOME="${ROOT_DIR}/airflow"
if command -v uv >/dev/null 2>&1; then
  if [ ! -f "${AIRFLOW_HOME}/airflow.db" ]; then
    info "Initializing Airflow database"
    uv run airflow db init || warn "Airflow not yet installed or failed to init; add it with 'uv add apache-airflow' if needed"
  else
    info "Airflow metadata DB already present"
  fi
else
  warn "uv unavailable; cannot run Airflow init"
fi

info "4) Optional: build Rust extractor (if crate present under src/)"
if [ -f src/Cargo.toml ]; then
  (cd src && cargo build --release)
else
  warn "src/Cargo.toml not found; skipping Rust build"
fi

info "5) Starting dev servers (set START_SERVERS=1 to auto-start)"
if [ "${START_SERVERS:-0}" -eq 1 ]; then
  info "Starting FastAPI (uvicorn) on http://localhost:8000"
  if uv run python - <<'PY'
import importlib.util
import sys

module_name = "tactics_training.api"
app_attr = "app"
if importlib.util.find_spec(module_name) is None:
    sys.exit(1)
mod = importlib.import_module(module_name)
if not hasattr(mod, app_attr):
    sys.exit(1)
PY
  then
    UVICORN_CMD=(uv run uvicorn tactics_training.api:app --host 0.0.0.0 --port 8000 --reload)
    "${UVICORN_CMD[@]}" &
    info "FastAPI running (PID $!)"
  else
    warn "FastAPI app not found yet; skipping start"
  fi

  if [ -f client/package.json ]; then
    info "Starting Vite dev server on http://localhost:5173"
    (cd client && npm run dev -- --host 0.0.0.0 --port 5173) &
    info "Vite running (PID $!)"
  fi

  if command -v uv >/dev/null 2>&1; then
    info "Starting Airflow webserver on http://localhost:8080"
    uv run airflow webserver -p 8080 &
    info "Airflow webserver running (PID $!)"
    info "Starting Airflow scheduler"
    uv run airflow scheduler &
    info "Airflow scheduler running (PID $!)"
  fi
else
  info "Skipping server startup. Set START_SERVERS=1 to auto-start backend/frontend/Airflow."
fi

cat <<'EOF'

Ready! Quick access summary:
- FastAPI (SSE, analytics API): http://localhost:8000 (uvicorn tactics_training.api:app)
- React dashboard (Vite): http://localhost:5173
- Airflow UI: http://localhost:8080 (user: admin / password you create)
- Practice + analytics endpoints: /api/stats/*, /api/tactics/search, /api/practice/next

If backend or frontend did not start, implement the app modules and re-run with START_SERVERS=1.
EOF
