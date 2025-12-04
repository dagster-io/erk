---
title: Sentinel Path Compatibility
read_when:
  - "writing functions that check path existence"
  - "seeing 'Called .exists() on sentinel path' errors"
  - "making functions testable with FakeGit"
---

# Sentinel Path Compatibility Pattern

## Problem

Functions that call `path.exists()` directly fail in tests using `erk_inmem_env()` because sentinel paths are not real filesystem paths.

## Solution: Optional git_ops Parameter

Add an optional `git_ops: Git | None` parameter to use `git_ops.path_exists()` instead of direct `.exists()` calls:

```python
def get_worktree_project(
    repo_dir: Path, worktree_name: str, git_ops: Git | None = None
) -> Path | None:
    worktrees_toml = repo_dir / "worktrees.toml"

    # Check existence using git_ops if provided (for test compatibility with fakes)
    if git_ops is not None:
        if not git_ops.path_exists(worktrees_toml):
            return None
    else:
        if not worktrees_toml.exists():
            return None
    # ... rest of function
```

## When to Apply

Apply this pattern when:

- Function checks path existence (`.exists()`, `.is_file()`, `.is_dir()`)
- Function is called from code that uses `ErkContext` (can pass `ctx.git`)
- Function needs to be testable with `erk_inmem_env()`

## Production vs Test Behavior

| Context                      | What Happens                           |
| ---------------------------- | -------------------------------------- |
| Production                   | `git_ops=None`, uses real `.exists()`  |
| Tests with `erk_inmem_env`   | Pass `ctx.git`, uses `FakeGit` methods |
| Tests with `erk_isolated_fs` | Either works (real paths exist)        |

## Related Topics

- [Testing](../testing/testing.md) - Fixture selection guide
- [Erk Architecture](erk-architecture.md) - Dependency injection patterns
