---
title: Parameter Injection Pattern
read_when:
  - eliminating monkeypatch from tests
  - adding testability to existing functions
  - refactoring functions that call global getters
tripwires:
  - action: "adding parameters for dependency injection"
    warning: "Use keyword-only syntax (`*,`) to prevent breaking existing positional parameter usage"
  - action: "tests with 3+ monkeypatch statements"
    warning: "Consider refactoring to parameter injection - see parameter-injection-pattern.md"
  - action: "refactoring that removes function calls from production code"
    warning: "Search for and remove associated test monkeypatch statements that are now dead. Dead patches clutter test files and confuse future readers."
---

# Parameter Injection Pattern

Replace internal function calls to global getters with explicit keyword-only parameters. This eliminates monkeypatch fragility and makes dependencies explicit.

## Problem

Functions that call `get_bundled_*_dir()` internally require `monkeypatch.setattr` in tests. This creates fragile tests that break when imports move between modules.

## Solution

Three-phase refactoring:

1. **Add keyword-only parameters** to functions that call getters internally
2. **Update callers** (CLI commands, health checks) to pass values from getters
3. **Remove internal getter calls** from the function bodies

## Pattern Structure

<!-- Source: src/erk/artifacts/artifact_health.py, find_orphaned_artifacts -->

See `find_orphaned_artifacts()` in `src/erk/artifacts/artifact_health.py` for the signature pattern with keyword-only bundled path parameters.

<!-- Source: src/erk/cli/commands/artifact/check.py -->

See the call sites in `src/erk/cli/commands/artifact/check.py` for the boundary function pattern - getters are called once and values passed to multiple core functions.

## Test Transformation

Tests calling functions directly pass parameters instead of monkeypatching:

<!-- Source: tests/artifacts/test_orphans.py -->

See test functions in `tests/artifacts/test_orphans.py` for the parameter injection test pattern.

## When to Use

- Functions with 3+ monkeypatch statements in tests
- Functions calling module-level getters for paths or configuration
- Core business logic functions (not CLI/boundary code)

## Related

- [Dependency Injection Boundaries](../architecture/dependency-injection-boundaries.md) - Architectural context
- [Monkeypatch Elimination Checklist](monkeypatch-elimination-checklist.md) - Broader migration guide
