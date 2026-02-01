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
		--cov-fail-under=95

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
	uv run vulture src/ \
		--min-confidence 60 \
		--ignore-decorators "@app.get,@app.post,@app.put,@app.patch,@app.delete" \
		--ignore-names "stockfish_ponder,move_number,analyze_positions,main,_clear_dashboard_cache,DbSchemas,analysis,insert_tactics,insert_tactic_outcomes,set_level,MockChessClient,MockDbStore,convert_raw_pgns_to_positions,run_monitor_new_positions,clock_seconds,applied_options,is_legal"

js-deadcode:
	cd client && npx knip

deadcode: py-deadcode js-deadcode

dup:
	cd client && npx jscpd \
		--format python,typescript,tsx,javascript,jsx \
		../src ./src \
		--min-lines 8 --min-tokens 70 --threshold 1 \
		--reporters console \
		--ignore "**/dist/**" \
		--ignore "**/coverage/**" \
		--ignore "**/node_modules/**" \
		--ignore "**/.venv/**" \
		--ignore "**/tests/**"

dedup: dup

build:
	uv run cargo build --release
	cd client && npm run build

dev:
	cd client && npm run dev --host --port 5178

check: lint test complexity dedup deadcode build

setup:
	@echo "Setting up the tactix repository..."
	@echo "1. Checking for Python..."
	@which python3 > /dev/null || (echo "Error: Python 3 not found. Please install Python 3.12+" && exit 1)
	@python3 --version
	@echo "2. Checking for Node.js..."
	@which node > /dev/null || (echo "Error: Node.js not found. Please install Node.js" && exit 1)
	@node --version
	@echo "3. Installing uv (if not already installed)..."
	@which uv > /dev/null || pip install uv
	@uv --version
	@echo "4. Running uv sync to set up Python virtual environment..."
	@uv sync
	@echo "5. Installing Node.js dependencies..."
	@cd client && npm install
	@echo "6. Installing pre-commit hooks..."
	@uv run pre-commit install
	@echo "✓ Setup complete! You can now run 'make check' to verify everything works."
