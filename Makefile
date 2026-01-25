pylint:
	uv run ruff check --fix src/
	uv run ruff format src/
	uv run ty check src/

jslint:
	cd client && npx eslint --fix . --ext .js,.jsx,.ts,.tsx
	cd client && npx prettier --write --cache .

lint: pylint jslint

pytest:
	uv run cargo test
	uv run cargo test --release
	uv run pytest tests/ --cov=src/ --cov-report=term-missing --cov-fail-under=95

jstest:
	cd client && npx jest --coverage --coverageThreshold='{"global": {"branches": 95, "functions": 95, "lines": 95, "statements": 95}}'

test: pytest jstest

build:
	uv run cargo build --release
	cd client && npm run build

dev:
	cd client && npm run dev --host --port 5178

check: lint test