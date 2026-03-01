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

`src/erk/core/health_checks.py` (1640 lines) was split into `src/erk/core/health_checks/` with 26 focused check modules, a shared model, and an orchestrator.

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
└── ... (26 check modules total)
```

## Key Principles

### 1. One Responsibility Per Module

Each module contains a single check function with a clear name matching the file:

- `erk_version.py` → `check_erk_version()`
- `github_cli.py` → `check_github_cli(shell)`
- `managed_artifacts.py` → `check_managed_artifacts(...)`

### 2. Shared Model in models.py

Common types live in a dedicated `models.py` to avoid circular imports:

```python
@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    message: str
    details: str | None = None
    remediation: str | None = None
```

### 3. Orchestrator **init**.py

The `__init__.py` imports all submodule functions explicitly and coordinates execution:

```python
"""Health checks orchestrator.

Submodules:
- anthropic_api_secret: check_anthropic_api_secret()
- claude_cli: check_claude_cli()
- erk_version: check_erk_version()
...
"""

from erk.core.health_checks.anthropic_api_secret import check_anthropic_api_secret
from erk.core.health_checks.claude_cli import check_claude_cli
from erk.core.health_checks.erk_version import check_erk_version
# ... all 26 imports

def run_all_checks(ctx: ErkContext, *, check_hooks: bool) -> list[CheckResult]:
    results = []
    results.append(check_erk_version())
    results.append(check_github_cli(ctx.shell))
    # ... conditional execution based on context
    return results
```

The import list serves dual purpose: dependency declaration and module index.

### 4. Lazy Imports for Heavy Dependencies

Gateway implementations and config loading are imported inside the orchestrator function, not at module level:

```python
def run_all_checks(ctx, *, check_hooks):
    # ... basic checks first ...
    if repo_ctx:
        from erk.cli.config import load_config
        from erk_shared.gateway.github.issues.real import RealGitHubIssues
        # ... use heavy dependencies only when needed
```

This prevents circular dependencies and speeds up import time for callers that only need individual checks.

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

```python
def check_github_cli(shell: Shell) -> CheckResult:
    gh_path = shell.get_installed_tool_path("gh")
    ...
```

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
