export UV_CACHE_DIR := tmp-logs/uv-cache
VENV_BIN ?= .venv/bin
RUFF ?= $(VENV_BIN)/ruff
PYLINT ?= $(VENV_BIN)/pylint
FLAKE8 ?= $(VENV_BIN)/flake8
TY ?= $(VENV_BIN)/ty
MYPY ?= $(VENV_BIN)/mypy
PYDOCSTYLE ?= $(VENV_BIN)/pydocstyle
PROSPECTOR ?= $(VENV_BIN)/prospector
PYTEST ?= $(VENV_BIN)/pytest
XENON ?= $(VENV_BIN)/xenon
PYCYCLE ?= $(VENV_BIN)/pycycle
VULTURE ?= $(VENV_BIN)/vulture
SAFETY ?= $(VENV_BIN)/safety
BANDIT ?= $(VENV_BIN)/bandit
DODGY ?= $(VENV_BIN)/dodgy

pylint:
# Ruff for linting and formatting 	
	$(RUFF) check --fix src/
	$(RUFF) format src/

# Pylint for additional linting
	PYLINTHOME=tmp-logs/pylint-cache $(PYLINT) --rcfile=pyproject.toml src/

# Flake8 for style guide enforcement
	$(FLAKE8) src/
	
# Ty for static type checking
	$(TY) check \
		--error deprecated \
		--ignore invalid-argument-type \
		--ignore invalid-method-override \
		--ignore invalid-type-form \
		--ignore unresolved-attribute \
		--ignore unresolved-import \
		--ignore unsupported-operator \
		src/

# Mypy for additional type checking
	$(MYPY) src/

# Pydocstyle for docstring style checking
	$(PYDOCSTYLE) src/

# Prospector for overall code quality analysis
	$(PROSPECTOR) -A src/


jslint:
	cd client && ./node_modules/.bin/eslint --fix . --ext .js,.jsx,.ts,.tsx
	cd client && if [ -x ./node_modules/.bin/prettier ]; then ./node_modules/.bin/prettier --write --cache .; else echo "prettier not installed; skipping"; fi

lint: pylint jslint

pytest:
# Cargo tests for Rust code
	cargo test
	cargo test --release

# Pytest for Python code with coverage
	$(PYTEST) tests/ \
		--cov=src/ \
		--cov-config=./.coveragerc \
		--cov-report=term-missing \
		--cov-fail-under=94.9

jstest:
	cd client && \
		./node_modules/.bin/vitest run \
		--coverage

test: pytest jstest

py-complexity:
# Xenon for code complexity analysis
	$(XENON) \
		--max-absolute A \
		--max-modules A \
		--max-average A \
		src/

# pycycle for detecting circular dependencies
	$(PYCYCLE) --here --ignore .venv,client,node_modules

complexity: py-complexity

py-deadcode:
# Vulture for dead code detection in Python
	$(VULTURE) src/ \
		--min-confidence 60 \
		--ignore-decorators "@app.get,@app.post,@app.put,@app.patch,@app.delete" \
		--ignore-names "stockfish_ponder,move_number,analyze_positions,main,_clear_dashboard_cache,DbSchemas,analysis,insert_tactics,insert_tactic_outcomes,set_level,MockChessClient,MockDbStore,convert_raw_pgns_to_positions,run_monitor_new_positions,clock_seconds,applied_options,is_legal,TIME_CONTROLS"

js-deadcode:
	cd client && ./node_modules/.bin/knip

deadcode: py-deadcode js-deadcode

dup:
	cd client && ./node_modules/.bin/jscpd \
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
	$(SAFETY) check --full-report
	$(BANDIT) -r src/ -lll
	$(DODGY) --max-line-complexity 10 src/

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
