---
title: Gateway-Specific Patterns
read_when:
  - "implementing gateway methods with mixed error handling"
  - "designing operations with main logic and cleanup steps"
  - "converting methods with cleanup operations to discriminated unions"
tripwires:
  - action: "converting a gateway method with cleanup operations to discriminated union"
    warning: "Main operation should return discriminated union, cleanup operations may remain exception-based if their failure indicates corrupted state. Document this mixed pattern clearly in method docstring."
---

# Gateway-Specific Patterns

Gateway methods sometimes require mixed exception/union handling when an operation has both a main action (which can fail expectedly) and cleanup steps (which indicate corrupted state if they fail).

## Mixed Exception/Union Handling in Single Methods

### The Pattern

When a gateway method combines:

1. **Main operation** - Can fail for expected, recoverable reasons → use discriminated union
2. **Cleanup operation** - Failure indicates corrupted state → remain exception-based

### Example: remove_worktree

The `remove_worktree` method demonstrates this pattern:

**Main operation** (`git worktree remove`):

- Can fail expectedly (worktree doesn't exist, in use, etc.)
- Returns `WorktreeRemoved | WorktreeRemoveError`

**Cleanup operation** (`git worktree prune`):

- Should never fail in normal operation
- If it fails, indicates corrupted repository state
- Remains exception-based (raises on failure)

**Implementation** (`real.py`):

```python
def remove_worktree(self, *, repo_root: Path, path: Path) -> WorktreeRemoved | WorktreeRemoveError:
    """Remove a worktree. Returns WorktreeRemoved on success, WorktreeRemoveError on failure.

    Note: Cleanup operations like 'git worktree prune' may still raise exceptions
    if they fail, as this indicates corrupted repository state requiring different handling.
    """
    # Main operation - discriminated union
    result = run_subprocess_with_context(
        ["git", "worktree", "remove", str(path)],
        cwd=repo_root,
        check=False,
    )

    if result.returncode != 0:
        return WorktreeRemoveError(
            path=path,
            message=f"Failed to remove worktree: {result.stderr}",
        )

    # Cleanup operation - exception-based (indicates corruption if fails)
    run_subprocess_with_context(
        ["git", "worktree", "prune"],
        cwd=repo_root,
        check=True,  # Raises SubprocessError if fails
    )

    return WorktreeRemoved(path=path)
```

### When to Apply This Pattern

Use mixed exception/union handling when:

1. **Main operation** has expected failure modes:
   - Resource doesn't exist
   - Resource is in use
   - Permission denied
   - Network timeout

2. **Cleanup operation** failures are exceptional:
   - Corrupted repository state
   - Filesystem corruption
   - Programming errors (shouldn't happen)

### LBYL Violation Fix

Before the discriminated union conversion, `delete_cmd.py:150-168` contained a LBYL violation:

```python
# BEFORE (LBYL violation)
def _remove_worktree_safe(ops: Operations, repo_root: Path, path: Path) -> None:
    """Remove worktree, catching errors."""
    try:
        ops.git_worktree.remove_worktree(repo_root=repo_root, path=path)
    except WorktreeRemoveError:
        pass  # Ignore errors
```

This wrapper function used try/except for control flow, violating erk's LBYL principle.

**After the discriminated union conversion:**

```python
# AFTER (LBYL-compliant)
result = ops.git_worktree.remove_worktree(repo_root=root, path=wt_path)
if isinstance(result, WorktreeRemoveError):
    click.echo(f"Warning: Failed to remove worktree: {result.message}", err=True)
    return 1
# Type narrowing: result is now WorktreeRemoved
```

The discriminated union pattern eliminates the need for try/except wrappers - callers check types before acting.

### Caller Expectations

Callers of methods with mixed exception/union handling should:

1. **Check discriminated union** for expected failures (main operation)
2. **NOT catch exceptions** for cleanup operations (let them propagate)

The exception from cleanup indicates a serious problem requiring immediate attention, not something to handle gracefully.

### Documentation Requirements

When implementing this pattern, the method docstring MUST document:

1. **Main operation return type** - Which discriminated union types
2. **Cleanup exceptions** - Which cleanup operations may raise
3. **Exception meaning** - What exceptions from cleanup indicate

Example docstring:

```python
def remove_worktree(self, *, repo_root: Path, path: Path) -> WorktreeRemoved | WorktreeRemoveError:
    """Remove a worktree. Returns WorktreeRemoved on success, WorktreeRemoveError on failure.

    Note: Cleanup operations like 'git worktree prune' may still raise exceptions
    if they fail, as this indicates corrupted repository state requiring different handling.
    """
```

### Reference Implementation

`packages/erk-shared/src/erk_shared/gateway/git/worktree/real.py` - `remove_worktree` method

PR #6346 - Complete conversion of `remove_worktree` to discriminated union with mixed exception handling

### Call Sites

12 call sites (4 production, 8 test) all use the same `isinstance()` pattern:

```python
result = ops.git_worktree.remove_worktree(repo_root=root, path=wt_path)
if isinstance(result, WorktreeRemoveError):
    # Handle expected failure
    click.echo(f"Warning: {result.message}", err=True)
# Continue - worktree removed successfully
```

None of the call sites wrap the operation in try/except because cleanup exceptions should propagate.

## Related Documentation

- [Discriminated Union Error Handling](discriminated-union-error-handling.md) - Core pattern for success/error unions
- [Gateway ABC Implementation](gateway-abc-implementation.md) - 5-place implementation checklist
- [LBYL Gateway Pattern](lbyl-gateway-pattern.md) - LBYL principles for gateway design
