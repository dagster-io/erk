---
title: Dependency Injection Boundaries
read_when:
  - deciding where to call configuration getters
  - structuring functions for testability
  - understanding the call site pattern
tripwires:
  - action: "calling global getters inside business logic functions"
    warning: "Consider parameter injection instead - call getters at boundaries, pass values to core functions"
---

# Dependency Injection Boundaries

Core business logic functions accept dependencies as explicit parameters. Boundary functions (CLI commands, health checks, entry points) resolve production dependencies by calling getters and passing values.

## Architecture

**Core Functions (Business Logic):**

- Accept dependencies as keyword-only parameters
- No imports of global getters
- Fully testable with any values
- Location: domain-specific modules (e.g., `artifact_health.py`)

**Boundary Functions (Integration):**

- Import and call production dependency getters
- Wire up real dependencies at the application boundary
- Location: CLI commands, health checks, entry points

## Benefits

1. **Testability**: Core functions testable with any Path values - no monkeypatch needed
2. **Explicit dependencies**: Reading function signature tells you all dependencies
3. **Clear architectural layers**: Boundaries handle wiring, core handles logic

## Example

<!-- Source: src/erk/artifacts/artifact_health.py, find_missing_artifacts -->

See `find_missing_artifacts()` in `src/erk/artifacts/artifact_health.py` for a core function accepting bundled paths as parameters.

<!-- Source: src/erk/cli/commands/artifact/check.py -->

See `check.py` for the boundary that imports `get_bundled_claude_dir()` and passes the result to core functions.

## Testing Strategy

- **Direct function tests**: Pass test paths as parameters (no monkeypatch)
- **CLI integration tests**: Monkeypatch at the boundary module (e.g., `check.py`)

## Related

- [Parameter Injection Pattern](../testing/parameter-injection-pattern.md) - Testing pattern details
- [Monkeypatch Elimination Checklist](../testing/monkeypatch-elimination-checklist.md) - Migration guide
