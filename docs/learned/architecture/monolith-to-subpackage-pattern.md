---
title: Monolith-to-Subpackage Refactoring Pattern
read_when:
  - "splitting a large module into a subpackage"
  - "refactoring monolithic files into focused modules"
  - "understanding the health_checks subpackage structure"
tripwires:
  - action: "re-exporting symbols from __init__.py after splitting a module"
    warning: "No re-exports. Each submodule has a canonical import path. The __init__.py is an orchestrator, not a facade."
  - action: "using wildcard imports in the orchestrator __init__.py"
    warning: "Use explicit imports for every submodule function. The import list doubles as a module index."
---

# Monolith-to-Subpackage Refactoring Pattern

When a single module exceeds ~500 lines with distinct responsibilities, split it into a subpackage with one module per function. The `__init__.py` becomes an orchestrator that coordinates the focused submodules.

## Exemplar: health_checks

`src/erk/core/health_checks.py` (1640 lines) was split into `src/erk/core/health_checks/` with 25 focused check modules, a shared model, and an orchestrator.

### Structure

```
health_checks/
├── __init__.py              # Orchestrator: run_all_checks()
├── models.py                # Shared types: CheckResult
├── anthropic_api_secret.py  # One check function each
├── claude_cli.py
├── erk_version.py
├── github_cli.py
├── managed_artifacts.py
└── ... (25 check modules total)
```

## Key Principles

### 1. One Responsibility Per Module

Each module contains a single check function with a clear name matching the file:

- `erk_version.py` → `check_erk_version()`
- `github_cli.py` → `check_github_cli(shell)`
- `managed_artifacts.py` → `check_managed_artifacts(...)`

### 2. Shared Model in models.py

Common types live in a dedicated `models.py` to avoid circular imports:

<!-- Source: src/erk/core/health_checks/models.py:6-28 -->

The `CheckResult` frozen dataclass holds eight fields: `name`, `passed`, `message`, plus optional `details`, `verbose_details`, `warning`, `info`, and `remediation`. All check functions return this type.

### 3. Orchestrator **init**.py

The `__init__.py` imports all submodule functions explicitly and coordinates execution:

<!-- Source: src/erk/core/health_checks/__init__.py -->

The orchestrator's module docstring lists every submodule and its check function, serving as a human-readable index. Below the docstring, explicit imports pull in all 25 check functions — this import list doubles as a dependency declaration and module index. The `run_all_checks(ctx, *, check_hooks)` function appends each check result to a list, with conditional execution based on context flags.

### 4. Lazy Imports for Heavy Dependencies

Gateway implementations and config loading are imported inside the orchestrator function, not at module level:

<!-- Source: src/erk/core/health_checks/__init__.py, run_all_checks() -->

Inside `run_all_checks()`, heavy dependencies like gateway implementations and config loading are imported lazily (via `from ... import ...` inside the function body) only when the relevant checks need them. This prevents circular dependencies and speeds up import time for callers that only need individual checks.

### 5. No Re-Exports

Each function has one canonical import path:

```python
# Correct: import from submodule
from erk.core.health_checks.managed_artifacts import check_managed_artifacts

# Wrong: re-export from __init__
from erk.core.health_checks import check_managed_artifacts  # Don't do this
```

### 6. Dependency Injection in Checks

Checks receive what they need as parameters rather than importing globals:

<!-- Source: src/erk/core/health_checks/github_cli.py:7-13 -->

For example, `check_github_cli(shell: Shell) -> CheckResult` takes a `Shell` instance as a parameter to locate the `gh` binary, rather than importing a global shell reference.

## When to Apply This Pattern

- Module exceeds ~500 lines with 5+ distinct functions
- Functions have separate concerns (each could be tested independently)
- Functions have different dependency requirements

## Test Migration

When splitting a module, update mock paths in tests to point to the new submodule locations:

```python
# Before: mock at monolithic path
mock.patch("erk.core.health_checks.check_github_cli")

# After: mock at submodule path
mock.patch("erk.core.health_checks.github_cli.check_github_cli")
```

## Related Documentation

- [Gateway ABC Implementation](gateway-abc-implementation.md) — Similar decomposition principles for gateway interfaces
- [Erk Architecture Patterns](erk-architecture.md) — Lightweight init, context regeneration patterns
