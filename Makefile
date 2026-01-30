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
	uv run pytest tests/ --cov=src/ --cov-config=./.coveragerc --cov-report=term-missing --cov-fail-under=90

jstest:
	cd client && \
		npx vitest run \
		--coverage

test: pytest jstest

py-complexity:
	uv run xenon \
		--max-absolute B \
		--max-modules B \
		--max-average B \
		src/

complexity: py-complexity

py-deadcode:
	uv run vulture src/ tests/ \
		--min-confidence 60

deadcode: py-deadcode

js-dup:
	cd client && npx jscpd \
		--min-lines 8 \
		--min-tokens 70 \
		--threshold 1 \
		--reporters console \
		--format typescript,tsx,javascript,jsx \
		--ignore "**/*.test.*","**/dist/**"\
		.

dedup: js-dup

build:
	uv run cargo build --release
	cd client && npm run build

dev:
	cd client && npm run dev --host --port 5178

check: lint test complexity deadcode build
