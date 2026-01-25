# Suggested commands

Project setup:
- chmod +x ./init.sh && ./init.sh
- START_SERVERS=1 ./init.sh (auto-start dev servers if available)

Docker (recommended):
- docker compose -f docker/compose.yml up --build -d
- docker compose -f docker/compose.yml down

Health checks:
- curl -s http://localhost:8000/api/health
- curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5173
- curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080

Lint/test/build (Makefile):
- make lint (ruff + ty + eslint/prettier)
- make test (cargo test + pytest + vitest)
- make check (lint + test)
- make build (cargo build + npm build)

Dev servers:
- cd client && npm run dev --host --port 5178
