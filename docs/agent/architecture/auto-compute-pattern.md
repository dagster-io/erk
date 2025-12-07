---
title: Auto-Compute Pattern for Context-Dependent Parameters
read_when:
  - "designing function APIs that need computed context"
  - "refactoring functions where callers forget to pass values"
  - "adding parameters that depend on current state"
---

# Auto-Compute Pattern for Context-Dependent Parameters

A pattern for reducing caller burden when functions need computed context values.

## Problem

Functions that require computed context (e.g., relative paths, current branch, worktree info) create a maintenance burden when callers must:

1. Remember to compute the value
2. Pass it correctly through multiple call sites
3. Update all call sites when the pattern changes

This leads to subtle bugs when callers forget to compute and pass the value.

## Solution

Auto-compute the value inside the function with a boolean opt-out flag:

```python
# BEFORE: Callers must compute and pass
def activate_worktree(
    ctx: ErkContext,
    repo: RepoContext,
    target_path: Path,
    script: bool,
    command_name: str,
    relative_path: Path | None = None,  # Easy to forget!
) -> None:
    ...

# AFTER: Auto-compute with opt-out
def activate_worktree(
    ctx: ErkContext,
    repo: RepoContext,
    target_path: Path,
    script: bool,
    command_name: str,
    preserve_relative_path: bool = True,  # Safe default, explicit opt-out
) -> None:
    relative_path: Path | None = None
    if preserve_relative_path:
        worktrees = ctx.git.list_worktrees(repo.root)
        relative_path = compute_relative_path_in_worktree(worktrees, ctx.cwd)
    ...
```

## Key Benefits

1. **Safe defaults**: New callers automatically get the correct behavior
2. **Explicit opt-out**: Callers who need different behavior set `preserve_relative_path=False`
3. **Single computation point**: Logic lives in one place, not scattered across callers
4. **Easier testing**: Tests can opt out with a simple boolean flag

## When to Use

- Context depends on current state (cwd, current branch, etc.)
- Multiple callers need the same computation
- Forgetting the parameter would cause subtle bugs
- The computation has no side effects

## When NOT to Use

- Caller needs fine-grained control over the value
- Computation is expensive and not always needed
- The value varies significantly between callers
- Caller already has the computed value (consider accepting both patterns)

## Example: Preserving Directory Position

The `activate_worktree()` function uses this pattern to preserve the user's relative directory position when switching worktrees:

```python
def activate_worktree(
    ctx: ErkContext,
    repo: RepoContext,
    target_path: Path,
    script: bool,
    command_name: str,
    preserve_relative_path: bool = True,
) -> None:
    """Activate a worktree, optionally preserving relative path position."""
    relative_path: Path | None = None
    if preserve_relative_path:
        worktrees = ctx.git.list_worktrees(repo.root)
        relative_path = compute_relative_path_in_worktree(worktrees, ctx.cwd)

    # Use relative_path when generating activation script
    script_content = render_activation_script(
        worktree_path=target_path,
        target_subpath=relative_path,  # None means just cd to worktree root
        final_message=f'echo "Switched to {target_path.name}"',
    )
```

## Related

- [`compute_relative_path_in_worktree()`](../glossary.md#compute_relative_path_in_worktree) - Utility function for computing relative paths
- [`render_activation_script()`](../glossary.md#render_activation_script) - Shell script generator that consumes the computed path
