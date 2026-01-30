# Potential Python Consolidation Opportunities

This report was generated after reading all Python files in the repository and scanning for semantically similar functions, helpers, and test patterns that are likely to benefit from consolidation.

Last updated: 2026-01-30 (post-consolidation scan)

## How this report was assembled

- Scanned all Python files under the repository (excluding virtualenv, node_modules, build artifacts).
- Identified repeated function names and recurring helper patterns.
- Reviewed major client modules and test suites for duplicated logic.

---

## High-priority consolidation candidates (remaining)

The items below are still present after the latest consolidation passes and are recommended for the next refactor cycles.

### A) Chess client fixture loader duplication across modules

Examples:

- load_fixture_games in [src/tactix/chess_clients/fetch_helpers.py](src/tactix/chess_clients/fetch_helpers.py)
- load_fixture_games in [src/tactix/pgn_utils.py](src/tactix/pgn_utils.py)

Reasoning: both are responsible for fixture PGN loading and filtering.

Consolidation idea: keep a single load helper in chess_clients/fetch_helpers.py and import it into pgn_utils.py (or vice versa).

---

### B) Client fixture usage decision helper duplicated

Examples:

- \_use_fixture_games in [src/tactix/chesscom_client.py](src/tactix/chesscom_client.py)
- \_use_fixture_games in [src/tactix/lichess_client.py](src/tactix/lichess_client.py)

Reasoning: identical purpose and signature, used to decide fixture fallback.

Consolidation idea: move to chess_clients/fetch_helpers.py and call from both clients.

---

### C) Game-row coercion helper duplicated

Examples:

- \_coerce_games in [src/tactix/chesscom_client.py](src/tactix/chesscom_client.py)
- \_coerce_games in [src/tactix/lichess_client.py](src/tactix/lichess_client.py)

Reasoning: both normalize raw rows into ChessGameRow models.

Consolidation idea: shared coercion helper in chess_clients/chess_game_row.py or chess_clients/fetch_helpers.py.

---

### D) Incremental fetch orchestration still split across client modules

Examples:

- fetch_incremental_games in [src/tactix/chesscom_client.py](src/tactix/chesscom_client.py)
- fetch_incremental_games in [src/tactix/lichess_client.py](src/tactix/lichess_client.py)
- fetch_incremental_games in [src/tactix/chess_clients/game_fetching.py](src/tactix/chess_clients/game_fetching.py)

Reasoning: similar orchestration flow still exists in multiple modules.

Consolidation idea: unify orchestration in chess_clients/game_fetching.py with per-source hooks.

---

### E) Raw PGN summary mapping still duplicated

Examples:

- fetch_raw_pgns_summary in [src/tactix/db/duckdb_store.py](src/tactix/db/duckdb_store.py)
- fetch_raw_pgns_summary in [src/tactix/postgres_store.py](src/tactix/postgres_store.py)

Reasoning: same output mapping logic for two backends.

Consolidation idea: shared mapper in src/tactix/db/raw_pgn_summary.py with light backend-specific wrappers.

---

### F) Duplicate test fixtures and HTTP fakes in tests

Examples:

- test_fixture_fetch_respects_since in [tests/test_chesscom_client.py](tests/test_chesscom_client.py) and [tests/test_lichess_client.py](tests/test_lichess_client.py)
- fake_get/json/raise_for_status helpers repeated in [tests/test_chesscom_client.py](tests/test_chesscom_client.py)

Reasoning: tests reimplement similar fake response patterns and shared assertions.

Consolidation idea: shared test helper module (tests/http_fakes.py) and shared fixture assertions.

---

## Completed consolidation items (for reference)

### 1) Airflow DAG defaults duplicated across DAGs

Examples:

- [airflow/dags/analyze_tactics.py](airflow/dags/analyze_tactics.py)
- [airflow/dags/daily_game_sync.py](airflow/dags/daily_game_sync.py)
- [airflow/dags/migrations.py](airflow/dags/migrations.py)
- [airflow/dags/monitor_new_positions.py](airflow/dags/monitor_new_positions.py)
- [airflow/dags/refresh_metrics.py](airflow/dags/refresh_metrics.py)

Reasoning: each file defines default_args with the same intent/config, which is ideal for a shared module (e.g., airflow/dags/\_defaults.py).

Consolidation idea: create a shared default_args() helper and import into each DAG.

---

### 2) Airflow DAG shared callbacks duplicated

Examples:

- notify_dashboard in [airflow/dags/analyze_tactics.py](airflow/dags/analyze_tactics.py)
- notify_dashboard in [airflow/dags/daily_game_sync.py](airflow/dags/daily_game_sync.py)
- notify_dashboard in [airflow/dags/monitor_new_positions.py](airflow/dags/monitor_new_positions.py)
- notify_dashboard in [airflow/dags/refresh_metrics.py](airflow/dags/refresh_metrics.py)

Reasoning: identical “notify” hooks are repeated across DAGs with the same behavior.

Consolidation idea: extract to airflow/dags/\_callbacks.py and import.

---

### 3) Airflow profile resolution duplicated

Examples:

- \_resolve_profile in [airflow/dags/daily_game_sync.py](airflow/dags/daily_game_sync.py)
- \_resolve_profile in [airflow/dags/monitor_new_positions.py](airflow/dags/monitor_new_positions.py)

Reasoning: repeated profile resolution logic is identical in purpose and usage.

Consolidation idea: move to a shared DAG helper module.

---

### 4) Chess.com client wrappers duplicate class methods

Examples (module-level wrappers mirroring ChesscomClient methods):

- \_get_with_backoff, \_load_fixture_games, \_fetch_archive_pages, \_fetch_remote_games, fetch_incremental_games in [src/tactix/chesscom_client.py](src/tactix/chesscom_client.py)

Reasoning: the wrapper functions simply re-instantiate a client and call methods, duplicating the API surface and logic paths.

Consolidation idea: keep a single public API by either:

- exporting the class methods only, or
- centralizing wrappers in a shared chess_clients/game_fetching.py and delegating there.

---

### 5) Chess.com/Lichess incremental fetch logic overlaps

Examples:

- fetch_incremental_games in [src/tactix/chesscom_client.py](src/tactix/chesscom_client.py)
- fetch_incremental_games in [src/tactix/lichess_client.py](src/tactix/lichess_client.py)
- fetch_incremental_games in [src/tactix/chess_clients/game_fetching.py](src/tactix/chess_clients/game_fetching.py)

Reasoning: same function name and workflow for different sources suggest a shared orchestration helper.

Consolidation idea: move shared flow to a single fetch_incremental_games in game_fetching.py, with per-source hooks injected.

---

### 6) Fixture loading and “use fixtures” logic duplicated

Examples:

- \_use_fixture_games in [src/tactix/chesscom_client.py](src/tactix/chesscom_client.py)
- \_use_fixture_games in [src/tactix/lichess_client.py](src/tactix/lichess_client.py)
- \_load_fixture_games in [src/tactix/chesscom_client.py](src/tactix/chesscom_client.py)
- \_load_fixture_games in [src/tactix/lichess_client.py](src/tactix/lichess_client.py)

Reasoning: these helpers implement the same decision and fixture-loading pattern across sources.

Consolidation idea: add a shared fixture loader in chess_clients/game_fetching.py and reuse it in both clients.

---

### 7) Game row coercion shared across chess clients

Examples:

- \_coerce_games in [src/tactix/chesscom_client.py](src/tactix/chesscom_client.py)
- \_coerce_games in [src/tactix/lichess_client.py](src/tactix/lichess_client.py)

Reasoning: same validation/normalization logic name and purpose.

Consolidation idea: common validator helper in a shared module, or reuse ChessGameRow.model_validate via a single shared function.

---

### 8) extract_pgn_metadata duplicated between base store and PGN utils

Examples:

- extract_pgn_metadata in [src/tactix/base_db_store.py](src/tactix/base_db_store.py)
- extract_pgn_metadata in [src/tactix/pgn_utils.py](src/tactix/pgn_utils.py)

Reasoning: same operation appears in both storage and utility layers.

Consolidation idea: keep a single implementation in pgn_utils.py and import in base_db_store.py.

---

### 9) Raw PGN summary query duplicated across storage backends

Examples:

- fetch_raw_pgns_summary in [src/tactix/db/duckdb_store.py](src/tactix/db/duckdb_store.py)
- fetch_raw_pgns_summary in [src/tactix/postgres_store.py](src/tactix/postgres_store.py)

Reasoning: same endpoint semantics across two backends with near-identical transformations.

Consolidation idea: centralize in BaseDbStore or a shared helper (data mapping extracted to shared function).

---

### 10) Normalized source helper duplicated

Examples:

- \_normalized_source in [src/tactix/pipeline.py](src/tactix/pipeline.py)
- \_normalized_source in [src/tactix/tactics_analyzer.py](src/tactix/tactics_analyzer.py)

Reasoning: same helper name indicates repeated logic with a single responsibility.

Consolidation idea: move to a shared utility (e.g., tactix/utils/source.py).

---

### 11) Repeated fixture-position helpers across tests

Examples:

- \_pin_fixture_position in multiple pin tests: [tests/test_pin_blitz.py](tests/test_pin_blitz.py), [tests/test_pin_bullet.py](tests/test_pin_bullet.py), [tests/test_pin_classical.py](tests/test_pin_classical.py), [tests/test_pin_correspondence.py](tests/test_pin_correspondence.py), [tests/test_pin_rapid.py](tests/test_pin_rapid.py)
- \_skewer_fixture_position in multiple skewer tests: [tests/test_skewer_blitz.py](tests/test_skewer_blitz.py), [tests/test_skewer_bullet.py](tests/test_skewer_bullet.py), [tests/test_skewer_classical.py](tests/test_skewer_classical.py), [tests/test_skewer_correspondence.py](tests/test_skewer_correspondence.py), [tests/test_skewer_rapid.py](tests/test_skewer_rapid.py)
- \_hanging_piece_fixture_position across hanging-piece tests: [tests/test_hanging_piece_blitz.py](tests/test_hanging_piece_blitz.py), [tests/test_hanging_piece_bullet.py](tests/test_hanging_piece_bullet.py), [tests/test_hanging_piece_classical.py](tests/test_hanging_piece_classical.py), [tests/test_hanging_piece_correspondence.py](tests/test_hanging_piece_correspondence.py), [tests/test_hanging_piece_rapid.py](tests/test_hanging_piece_rapid.py)

Reasoning: repeated fixtures strongly suggest shared test fixtures.

Consolidation idea: create tests/fixture_helpers.py with shared fixture builders and import from tests.

---

### 12) Duplicate tests for Stockfish runner utilities

Examples:

- test_analyse_fallback_material_score in [tests/test_stockfish_checksum.py](tests/test_stockfish_checksum.py) and [tests/test_stockfish_runner.py](tests/test_stockfish_runner.py)
- test_resolve_command_prefers_existing_path in [tests/test_stockfish_checksum.py](tests/test_stockfish_checksum.py) and [tests/test_stockfish_runner.py](tests/test_stockfish_runner.py)
- test_resolve_command_uses_shutil_which in [tests/test_stockfish_checksum.py](tests/test_stockfish_checksum.py) and [tests/test_stockfish_runner.py](tests/test_stockfish_runner.py)
- test_build_limit_prefers_depth in [tests/test_stockfish_checksum.py](tests/test_stockfish_checksum.py) and [tests/test_stockfish_runner.py](tests/test_stockfish_runner.py)
- test_restart_handles_engine_quit_errors in [tests/test_stockfish_checksum.py](tests/test_stockfish_checksum.py) and [tests/test_stockfish_runner.py](tests/test_stockfish_runner.py)

Reasoning: identical tests across two files.

Consolidation idea: move shared tests into a single test module or shared helper functions.

---

### 13) Duplicate API tests

Examples:

- test_migrations_job_skips_cache_refresh in [tests/test_api_jobs.py](tests/test_api_jobs.py) and [tests/test_api_profile.py](tests/test_api_profile.py)

Reasoning: same test behavior duplicated in different API test files.

Consolidation idea: keep in one canonical file or share a helper.

---

### 14) Repeated “find missed/failed attempt” helper logic in tests and tmp-logs

Examples:

- \_find_missed_position and \_find_failed_attempt_position repeated across many test modules such as [tests/test_discovered_attack_classical.py](tests/test_discovered_attack_classical.py), [tests/test_discovered_check_blitz_low.py](tests/test_discovered_check_blitz_low.py), [tests/test_mate_in_one_rapid.py](tests/test_mate_in_one_rapid.py), [tests/test_mate_in_two_blitz.py](tests/test_mate_in_two_blitz.py), [tests/test_pin_correspondence.py](tests/test_pin_correspondence.py), [tests/test_skewer_correspondence.py](tests/test_skewer_correspondence.py)

Reasoning: this is a stable “query helper” pattern ideal for a shared test helper.

Consolidation idea: extract into tests/fixture_helpers.py or tests/query_helpers.py.

---

### 15) tmp-logs seed scripts share a common \_ensure_position

Examples:

- \_ensure_position repeated in many seed scripts, e.g. [tmp-logs/feature_186_seed_outcome_found_discovered_attack_correspondence.py](tmp-logs/feature_186_seed_outcome_found_discovered_attack_correspondence.py) and multiple related seed scripts in tmp-logs.

Reasoning: common seeding and fixture preparation logic repeated across many scripts.

Consolidation idea: create a shared seeding helper in tmp-logs/\_seed_helpers.py and import it in each seed script.

---

## Suggested next refactor step

If you want to proceed with refactoring, the highest impact and lowest-risk consolidation appears to be shared helpers for the chess client fixture logic plus shared HTTP fake helpers in tests. These would reduce repetition across core code and tests without changing external behavior.
