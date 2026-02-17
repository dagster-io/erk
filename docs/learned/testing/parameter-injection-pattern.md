---
title: Bundled Path Parameter Injection for Testability
category: testing
read_when:
  - "adding functions that need access to bundled .claude/ directory"
  - "testing code that references get_bundled_claude_dir()"
  - "making internal path lookups testable"
tripwires:
  - action: "calling get_bundled_claude_dir() inside a testable function"
    warning: "Accept bundled_claude_dir as a parameter instead. Production callers pass get_bundled_claude_dir(), tests pass tmp_path / 'bundled'. Read this doc."
---

# Bundled Path Parameter Injection for Testability

Functions that need the bundled `.claude/` directory path accept it as a parameter rather than calling `get_bundled_claude_dir()` internally. This makes them testable without monkeypatching.

## The Pattern

Instead of:

```python
# BAD: Hard to test, requires monkeypatching
def find_orphaned_artifacts(project_claude_dir: Path) -> list[str]:
    bundled = get_bundled_claude_dir()  # Internal call
    ...
```

Use:

```python
# GOOD: Testable via parameter injection
def find_orphaned_artifacts(
    project_claude_dir: Path,
    bundled_claude_dir: Path,
) -> list[str]:
    ...
```

## Production vs Test Usage

**Production callers** pass the real path:

```python
from erk.artifacts.sync import get_bundled_claude_dir

result = find_orphaned_artifacts(
    project_claude_dir=project_root / ".claude",
    bundled_claude_dir=get_bundled_claude_dir(),
)
```

**Tests** pass a temporary directory:

```python
def test_find_orphaned_artifacts(tmp_path: Path) -> None:
    bundled_dir = tmp_path / "bundled"
    bundled_dir.mkdir()
    # Set up test fixtures in bundled_dir...

    result = find_orphaned_artifacts(
        project_claude_dir=tmp_path / ".claude",
        bundled_claude_dir=bundled_dir,
    )
```

## Where This Pattern Is Used

The artifact health module applies this pattern consistently:

| Function                    | File                                   |
| --------------------------- | -------------------------------------- |
| `get_artifact_health()`     | `src/erk/artifacts/artifact_health.py` |
| `find_orphaned_artifacts()` | `src/erk/artifacts/artifact_health.py` |
| `find_missing_artifacts()`  | `src/erk/artifacts/artifact_health.py` |

Tests:

| Test File                                 | Pattern                       |
| ----------------------------------------- | ----------------------------- |
| `tests/artifacts/test_artifact_health.py` | Uses `tmp_path` for both dirs |
| `tests/artifacts/test_orphans.py`         | Uses `tmp_path / "bundled"`   |
| `tests/artifacts/test_missing.py`         | Uses `tmp_path / "bundled"`   |

## Why Not Monkeypatching

Parameter injection is preferred over monkeypatching because:

- **Explicit dependencies**: The function signature documents what it needs
- **No import-time side effects**: `get_bundled_claude_dir()` may be cached (`@lru_cache`) — monkeypatching after import is fragile
- **Parallel-safe**: No global state to conflict between concurrent tests
- **LBYL-compatible**: Aligns with erk's preference for explicit over implicit dependencies
