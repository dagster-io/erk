---
title: Gateway Error Boundaries
read_when:
  - "implementing try/except in gateway real.py files"
  - "designing error boundaries for subprocess calls"
  - "understanding where exceptions become discriminated unions"
tripwires:
  - action: "adding try/except in gateway real.py for subprocess calls"
    warning: "Catch specific exceptions (RuntimeError, CalledProcessError) and return discriminated union error types. Never re-raise — errors become return values at this boundary."
  - action: "using template.format() without verifying placeholders exist in the template"
    warning: "Assert that required placeholders exist in the template string before calling .format(). Missing placeholders cause silent formatting failures or KeyError at runtime."
---

# Gateway Error Boundaries

Gateway `real.py` files are the boundary where subprocess exceptions become discriminated union return values. This pattern ensures all code above the gateway layer uses LBYL (`isinstance()` checks) instead of try/except.

## The Pattern

```python
# real.py — the ONLY place try/except is acceptable for expected failures
def push_to_remote(
    self,
    cwd: Path,
    remote: str,
    branch: str,
    *,
    set_upstream: bool,
    force: bool,
) -> PushResult | PushError:
    cmd = ["git", "push", remote, branch]
    if set_upstream:
        cmd.extend(["--set-upstream"])
    if force:
        cmd.extend(["--force-with-lease"])
    try:
        run_subprocess_with_context(cmd, cwd=cwd)
        return PushResult()
    except RuntimeError as e:
        return PushError(message=str(e))
```

## Key Rules

1. **`real.py` is the error boundary**: Try/except wraps subprocess calls and converts exceptions to discriminated union error types
2. **Fakes return directly**: `fake.py` returns configured success or error variants — no exceptions
3. **Dry-run returns success**: `dry_run.py` returns the success variant without executing
4. **Printing delegates**: `printing.py` logs then delegates to wrapped implementation
5. **Callers use isinstance()**: All code above the gateway uses `isinstance(result, ErrorType)` — never try/except

## Reference Implementation

`packages/erk-shared/src/erk_shared/gateway/git/remote_ops/real.py`:

- `push_to_remote()` (lines 66–91): Wraps `run_subprocess_with_context()`, catches `RuntimeError`, returns `PushResult | PushError`
- `pull_rebase()` (lines 93–105): Same pattern, returns `PullRebaseResult | PullRebaseError`

## Anti-Patterns

```python
# WRONG: try/except in business logic (above gateway layer)
try:
    result = ctx.git.remote.push_to_remote(cwd, "origin", branch, ...)
except RuntimeError:
    handle_error()

# CORRECT: isinstance check in business logic
result = ctx.git.remote.push_to_remote(cwd, "origin", branch, ...)
if isinstance(result, PushError):
    handle_error(result.message)
```

## Related Documentation

- [Discriminated Union Error Handling](discriminated-union-error-handling.md) — The union types returned at these boundaries
- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) — The 5-place pattern for gateway implementations
- [Subprocess Wrappers](subprocess-wrappers.md) — The subprocess functions wrapped at these boundaries
