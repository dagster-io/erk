---
title: Fakes Directory Structure
read_when:
  - "creating a new fake for testing"
  - "deciding where to put a fake class"
  - "understanding where test infrastructure lives"
tripwires:
  - action: "creating a fake class in src/"
    warning: "Fakes belong in tests/fakes/, not in production code. Production code should not contain test doubles. Move the fake to tests/fakes/gateway/ or tests/fakes/tests/ depending on whether it's a gateway fake or a test-specific double."
---

# Fakes Directory Structure

Test fakes in erk live in `tests/fakes/`, not in production code under `src/`.

## Directory Layout

```
tests/
└── fakes/
    ├── __init__.py
    ├── gateway/           # Fake gateway implementations
    │   └── ...            # FakeGit, FakeGitHub, etc.
    └── tests/             # Test-specific doubles
        ├── health_check_runner.py    # FakeHealthCheckRunner
        ├── parallel_task_runner.py   # FakeParallelTaskRunner
        ├── tui_plan_data_provider.py # FakePrDataProvider
        └── ...
```

## Why Not `src/`?

Production code should not depend on test infrastructure. Placing fakes in `src/` would:
1. Increase the production package size
2. Create circular dependencies (production code importing test tools)
3. Violate the principle that `src/` contains only deployable artifacts

## Where to Put New Fakes

| Fake Type | Location |
|---|---|
| Gateway fake (FakeGit, FakeGitHub, etc.) | `tests/fakes/gateway/` |
| Test-specific double for a service/component | `tests/fakes/tests/` |

## Related Documentation

- [Testing Patterns](testing.md) — Full 5-layer testing architecture
- [Fake-Driven Testing Skill](../../../.claude/skills/fake-driven-testing/) — Comprehensive fake usage patterns
