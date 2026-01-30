
# Architecture & Code Design Principles

## Layered Architecture

- **Core primitives**: Small, stateless modules for basic operations (e.g., `fen::FenString`, `chess::Move`, `tactics::TacticType`). Responsibilities: data representation, parsing, and validation. No I/O or orchestration logic.
- **Domain services**: Modules that encapsulate domain logic (e.g., `game_fetcher`, `fen_converter`, `tactics_finder`). They compose primitives, handle errors, and expose clear APIs. No direct CLI, HTTP, or DB code.
- **Integration/adapters**: Handle external boundaries (e.g., HTTP clients, CLI parsing, database access). They call domain services, manage configuration, and translate between external and internal types.
- **No mixing of concerns**: Parsing, business logic, and I/O are separated. Each layer only depends on the one below it.

## Extraction & Modularity

Extract a new module/class/function when:

- Logic is reused in 2+ places, or
- It represents a single, well-defined operation (e.g., “convert PGN to FEN”), or
- It bundles domain concepts (e.g., `Tactic`, `GamePosition`).

Checklist for a good module/function:

- **Name describes intent**: `find_tactics`, `fetch_games`, `to_fen_string`.
- **Encapsulates domain details**: Callers shouldn’t reconstruct FENs or parse PGN manually.
- **Minimal API**: Accept only what’s needed (e.g., a `Game` object, not raw strings).
- **Explicit errors**: Return `Result`/`Option` (Rust) or raise/return errors (Python) clearly.
- **No leakage of external types**: Domain logic should not depend on HTTP/DB/CLI types.

## Refactor Heuristics

Look for:

- **State or config passed through many layers**: e.g., passing DB handles, config, or logger everywhere.
- **Inline orchestration in main/entrypoint**: Main should only wire up services, not contain logic.
- **Duplicated parsing/validation**: Parsing FEN/PGN or finding tactics in multiple places.
- **Large functions that do multiple things**: Split into helpers or new modules.

## What to Extract

- **Domain services**: e.g., `TacticsFinder`, `FenConverter`.
- **Adapters**: e.g., `HttpGameFetcher`, `CliRunner`.
- **Helpers**: e.g., `parse_pgn`, `validate_fen`.

## API & Error Handling

- **No panics/unwraps in library code**: Use `Result`/`Option` (Rust) or exceptions (Python).
- **Return domain errors**: Define error types for parsing, fetching, and analysis.
- **Stable function signatures**: Don’t change argument types/names for the same operation.

## Imports & Boundaries

- Use **project-relative imports**.
- Keep domain logic free of external dependencies (HTTP, DB, CLI).
- Folder structure:
  - `core/`: primitives and domain types
  - `services/`: domain logic
  - `adapters/`: I/O, integration, CLI, HTTP
  - `bin/` or `main.py`: entrypoints only

## Function Size & Responsibility

- Functions ≤10 lines (prefer ≤5) and single-responsibility.
- Extract helpers for parsing, validation, and transformation.
- Prefer many small modules over monoliths.

## Naming Convention (Verb/Object/Details)

Use the pattern:

```
<verb>_<object>__<details>
```

Examples:

- `fetch_games__chesscom_archive`
- `prepare_payload__refresh_metrics`
- `orchestrate_pipeline__daily_game_sync`
- `gather_positions__recent`
- `import_settings__from_env`

Verb definitions:

- `import`: reading from another module or local source
- `gather`: collecting data for a later step
- `fetch`: network request (HTTP, API)
- `prepare`: building or shaping data for another task (payloads, filters)
- `orchestrate`: coordinating multiple steps or helpers

If a function cannot be named with this pattern, it is too complex and must be split into smaller helpers plus an orchestrator.

## Testing Requirements

- **100% unit test coverage for core/services**.
- Each helper and service must have direct unit tests.
- Integration tests for adapters and entrypoints.
- Add tests alongside code; do not defer.

## Patterns to Avoid

- Mixing parsing, business logic, and I/O in one function.
- Duplicating FEN/PGN parsing or tactic detection.
- Large, untested functions.
- Unhandled errors or panics in library code.

## Pre-commit Expectations

- Commits must pass: formatting, lint, type-check, and tests with coverage.
- Hooks should run from repo root and apply to all packages.
