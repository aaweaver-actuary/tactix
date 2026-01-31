#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

info() { printf "[init] %s\n" "$*"; }
warn() { printf "[init][warn] %s\n" "$*"; }
error() { printf "[init][error] %s\n" "$*"; }

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

info "3) Docker compose (recommended runtime)"
if [ "${START_DOCKER:-1}" -eq 1 ]; then
  if command -v docker >/dev/null 2>&1; then
    info "Starting Docker Compose stack (docker/compose.yml)"
    docker compose -f docker/compose.yml up -d || warn "Docker compose failed; check Docker Desktop/daemon"
  else
    warn "docker not found; install Docker Desktop or set START_DOCKER=0"
  fi
else
  info "Skipping Docker Compose. Set START_DOCKER=1 to auto-start services."
fi

info "4) Airflow bootstrap (optional; set AIRFLOW_INIT=1)"
export AIRFLOW_HOME="${ROOT_DIR}/airflow"
if [ "${AIRFLOW_INIT:-0}" -eq 1 ]; then
  if command -v uv >/dev/null 2>&1; then
    if [ ! -f "${AIRFLOW_HOME}/airflow.db" ]; then
      info "Initializing Airflow database"
      uv run airflow db init || warn "Airflow not yet installed or failed to init; add it with 'uv add apache-airflow' if needed"
    else
      info "Airflow metadata DB already present"
    fi
    AIRFLOW_ADMIN_USERNAME="${AIRFLOW_ADMIN_USERNAME:-admin}"
    AIRFLOW_ADMIN_PASSWORD="${AIRFLOW_ADMIN_PASSWORD:-admin}"
    AIRFLOW_ADMIN_EMAIL="${AIRFLOW_ADMIN_EMAIL:-admin@example.com}"
    AIRFLOW_ADMIN_FIRSTNAME="${AIRFLOW_ADMIN_FIRSTNAME:-Admin}"
    AIRFLOW_ADMIN_LASTNAME="${AIRFLOW_ADMIN_LASTNAME:-User}"

    if ! uv run airflow users list | awk 'NR>2 {print $1}' | grep -qx "${AIRFLOW_ADMIN_USERNAME}"; then
      info "Creating Airflow admin user ${AIRFLOW_ADMIN_USERNAME}"
      uv run airflow users create \
        --username "${AIRFLOW_ADMIN_USERNAME}" \
        --password "${AIRFLOW_ADMIN_PASSWORD}" \
        --firstname "${AIRFLOW_ADMIN_FIRSTNAME}" \
        --lastname "${AIRFLOW_ADMIN_LASTNAME}" \
        --role Admin \
        --email "${AIRFLOW_ADMIN_EMAIL}" \
        || warn "Failed to create Airflow admin user; ensure Airflow metadata DB is initialized"
    fi
  else
    warn "uv unavailable; cannot run Airflow init"
  fi
else
  info "Skipping Airflow bootstrap. Set AIRFLOW_INIT=1 to initialize metadata DB."
fi

info "5) Optional: build Rust extractor (if crate present under src/)"
if [ -f src/Cargo.toml ]; then
  (cd src && cargo build --release)
else
  warn "src/Cargo.toml not found; skipping Rust build"
fi

info "6) Starting dev servers (set START_SERVERS=1 to auto-start)"
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

info "\n\nPinging services to verify startup..."
sleep 1
IS_VERIFIED=1
info "FastAPI health check:"
if !curl --max-time 10 -s http://localhost:8000/api/health 
then
  warn "FastAPI health check failed"
  IS_VERIFIED=0
fi
info "Vite root endpoint check:"
HTTP_CODE=$(curl --max-time 10 -s -o /dev/null -w "%{http_code}\n" http://localhost:5173) || warn "Vite root endpoint check failed"
if [ "$HTTP_CODE" -ne 200 ]; then
  warn "Vite root endpoint returned HTTP $HTTP_CODE"
  IS_VERIFIED=0
fi
info "Airflow webserver endpoint check:"
HTTP_CODE=$(curl --max-time 10 -s -o /dev/null -w "%{http_code}\n" http://localhost:8080) || warn "Airflow webserver endpoint check failed"
if [ "$HTTP_CODE" -ne 200 ]; then
  warn "Airflow webserver endpoint returned HTTP $HTTP_CODE"
  IS_VERIFIED=0
fi

if [ "$IS_VERIFIED" -eq 1 ]; then
  info "All services responded successfully."
else
  error "One or more services did not respond successfully."
fi

cat <<'EOF'


Ready! Quick access summary:
- FastAPI (SSE, analytics API): http://localhost:8000 (uvicorn tactics_training.api:app)
- React dashboard (Vite): http://localhost:5173
- Airflow UI: http://localhost:8080 (user: admin / password you create)
- Practice + analytics endpoints: /api/stats/*, /api/tactics/search, /api/practice/next

If backend or frontend did not start, implement the app modules and re-run with START_SERVERS=1.
