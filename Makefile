pylint:
# Ruff for linting and formatting 	
	uv run ruff check --fix src/
	uv run ruff format src/

# Pylint for additional linting
	PYLINTHOME=tmp-logs/pylint-cache uv run pylint --rcfile=pyproject.toml src/

# Flake8 for style guide enforcement
	uv run flake8 src/
	
# Ty for static type checking
	uv run ty check \
		--error deprecated \
		--ignore invalid-argument-type \
		--ignore invalid-method-override \
		--ignore invalid-type-form \
		--ignore unresolved-attribute \
		--ignore unresolved-import \
		--ignore unsupported-operator \
		src/

# Mypy for additional type checking
	uv run mypy src/

# Pydocstyle for docstring style checking
	uv run pydocstyle src/

# Prospector for overall code quality analysis
	uv run prospector -A src/


jslint:
	cd client && npx eslint --fix . --ext .js,.jsx,.ts,.tsx
	cd client && npx prettier --write --cache .

lint: pylint jslint

pytest:
# Cargo tests for Rust code
	uv run cargo test
	uv run cargo test --release

# Pytest for Python code with coverage
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
# Xenon for code complexity analysis
	uv run xenon \
		--max-absolute A \
		--max-modules A \
		--max-average A \
		src/

# pycycle for detecting circular dependencies
	uv run pycycle --here

complexity: py-complexity

py-deadcode:
# Vulture for dead code detection in Python
	uv run vulture src/ \
		--min-confidence 60 \
		--ignore-decorators "@app.get,@app.post,@app.put,@app.patch,@app.delete" \
		--ignore-names "stockfish_ponder,move_number,analyze_positions,main,_clear_dashboard_cache,DbSchemas,analysis,insert_tactics,insert_tactic_outcomes,set_level,MockChessClient,MockDbStore,convert_raw_pgns_to_positions,run_monitor_new_positions,clock_seconds,applied_options,is_legal,TIME_CONTROLS"

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

pyguard:
	uv run safety check --full-report
	uv run bandit -r src/ -lll
	uv run dodgy --max-line-complexity 10 src/

guard: pyguard

build:
	uv run cargo build --release
	cd client && npm run build

dev:
	cd client && npm run dev --host --port 5178

check: lint test complexity guard dedup deadcode build

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
