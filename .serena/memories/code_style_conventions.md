# Code style & conventions

- Layered architecture: core primitives (no I/O) → domain services → adapters/integrations.
- Keep functions small (≤10 lines, prefer ≤5) and single responsibility; extract helpers when logic is reused or domain-specific.
- Avoid mixing parsing, business logic, and I/O in one function.
- Use explicit errors (no panics/unwraps in library code); keep stable function signatures.
- Prefer project-relative imports; keep domain logic free of HTTP/DB/CLI types.
- Tests expected for helpers/services; integration tests for adapters/entrypoints.
