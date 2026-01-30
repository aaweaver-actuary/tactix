pylint:
	uv run ruff check --fix src/
	uv run ruff format src/
	uv run ty check \
		--error deprecated \
		src/

jslint:
	cd client && npx eslint --fix . --ext .js,.jsx,.ts,.tsx
	cd client && npx prettier --write --cache .

lint: pylint jslint

pytest:
	uv run cargo test
	uv run cargo test --release
	uv run pytest tests/ \
		--cov=src/ \
		--cov-config=./.coveragerc \
		--cov-report=term-missing \
		--cov-fail-under=90

jstest:
	cd client && \
		npx vitest run \
		--coverage

test: pytest jstest

py-complexity:
	uv run xenon \
		--max-absolute A \
		--max-modules A \
		--max-average A \
		src/

complexity: py-complexity

py-deadcode:
	uv run vulture src/ tests/ \
		--min-confidence 60

js-deadcode:
	cd client && npx knip

deadcode: py-deadcode js-deadcode

dup:
	cd client && npx jscpd \
		--format python,typescript,tsx,javascript,jsx \
		--path .. \
		--min-lines 8 --min-tokens 70 --threshold 1 \
		--reporters console \
		--ignore "**/dist/**,**/coverage/**,**/node_modules/**,**/.venv/**"

dedup: dup

build:
	uv run cargo build --release
	cd client && npm run build

dev:
	cd client && npm run dev --host --port 5178

check: lint test complexity dedup deadcode build
