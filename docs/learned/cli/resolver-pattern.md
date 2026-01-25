---
title: Resolver Pattern
read_when:
  - "creating thin resolver functions"
  - "normalizing different input types to common output"
  - "understanding _resolve_* function naming convention"
  - "implementing entry-point-specific resolution logic"
---

# Resolver Pattern

Thin functions that normalize different input formats into a single output type, enabling unified downstream code paths.

## Pattern Structure

A resolver function:

1. Takes entry-point-specific arguments
2. Performs entry-point-specific validation and resolution
3. Returns a unified output type
4. Uses the `_resolve_*` naming convention

```python
def _resolve_land_target_pr(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    pr_number: int,
    up_flag: bool,
) -> LandTarget:
    """Resolve landing target from PR number."""
    # 1. Fetch PR details
    pr_details = ctx.github.get_pr(repo.owner, repo.name, pr_number)

    # 2. Determine worktree association
    worktree_path = _find_worktree_for_branch(ctx, pr_details.head_branch)

    # 3. Return unified type
    return LandTarget(
        branch=pr_details.head_branch,
        pr_details=pr_details,
        worktree_path=worktree_path,
        is_current_branch=False,
        use_graphite=_should_use_graphite(ctx, pr_details.head_branch),
        target_child_branch=_resolve_up_target(ctx, up_flag) if up_flag else None,
    )
```

## Examples in Codebase

| Function                                | Input           | Output        | Location               |
| --------------------------------------- | --------------- | ------------- | ---------------------- |
| `_resolve_land_target_current_branch()` | Current context | `LandTarget`  | land_cmd.py            |
| `_resolve_land_target_pr()`             | PR number       | `LandTarget`  | land_cmd.py            |
| `_resolve_land_target_branch()`         | Branch name     | `LandTarget`  | land_cmd.py            |
| `_resolve_current_worktree()`           | Current path    | `Path`        | stack/move_cmd.py      |
| `_resolve_session_id()`                 | Various sources | `str \| None` | exec/scripts/marker.py |
| `detect_target_type()`                  | Target string   | `TargetInfo`  | implement_shared.py    |

## Design Guidelines

### Use Keyword-Only Arguments

After the first positional argument, use `*` to force keyword arguments:

```python
def _resolve_target(
    ctx: ErkContext,
    *,                    # Forces keyword-only below
    repo: RepoContext,
    pr_number: int,
) -> Target:
```

### Return Frozen Dataclasses

The output type should be a frozen dataclass with all fields required:

```python
@dataclass(frozen=True)
class LandTarget:
    branch: str                      # Always present
    pr_details: PRDetails            # Always present
    worktree_path: Path | None       # Optional field uses None
    is_current_branch: bool          # Always present
```

### Handle Errors Early

Resolvers should validate and fail fast, not return partial results:

```python
def _resolve_land_target_pr(ctx: ErkContext, *, pr_number: int) -> LandTarget:
    pr = ctx.github.get_pr(owner, repo, pr_number)

    # Fail fast if PR not found
    if isinstance(pr, PRNotFound):
        raise click.ClickException(f"PR #{pr_number} not found")

    # Fail fast if PR already merged
    if pr.merged_at is not None:
        raise click.ClickException(f"PR #{pr_number} is already merged")

    return LandTarget(...)
```

### Keep Resolvers Thin

Resolvers should focus on input normalization, not business logic:

```python
# GOOD - thin resolver
def _resolve_target(ctx, *, branch: str) -> Target:
    worktree = _find_worktree(ctx, branch)
    pr = _fetch_pr(ctx, branch)
    return Target(branch=branch, worktree=worktree, pr=pr)

# BAD - too much business logic
def _resolve_target(ctx, *, branch: str) -> Target:
    worktree = _find_worktree(ctx, branch)
    if worktree:
        _validate_worktree_state(worktree)  # Business logic
        _sync_with_remote(ctx, branch)       # Side effect
    # ... more logic
```

## Dispatch Pattern

Use a simple dispatch in the main command:

```python
def command(target: str | None) -> None:
    if target is None:
        resolved = _resolve_from_current_context(ctx)
    elif target.isdigit():
        resolved = _resolve_from_pr(ctx, pr_number=int(target))
    elif "github.com" in target:
        resolved = _resolve_from_url(ctx, url=target)
    else:
        resolved = _resolve_from_branch(ctx, branch=target)

    # Single downstream path
    _execute(ctx, target=resolved)
```

## Testing Resolvers

Test each resolver independently:

```python
def test_resolve_from_pr_returns_land_target() -> None:
    """Resolver should return LandTarget with PR details."""
    ctx = context_for_test(github=FakeGitHub(...))

    target = _resolve_land_target_pr(ctx, repo=repo, pr_number=123, up_flag=False)

    assert target.branch == "feature-branch"
    assert target.pr_details.number == 123
    assert target.is_current_branch is False


def test_resolve_from_pr_raises_on_not_found() -> None:
    """Resolver should raise ClickException for missing PR."""
    ctx = context_for_test(github=FakeGitHub(prs=[]))  # No PRs

    with pytest.raises(click.ClickException, match="PR #123 not found"):
        _resolve_land_target_pr(ctx, repo=repo, pr_number=123, up_flag=False)
```

## Related Topics

- [Multi-Entry-Point Commands](multi-entry-point-commands.md) - Higher-level pattern using resolvers
- [Frozen Dataclass Patterns](../architecture/frozen-dataclass-patterns.md) - Output type guidelines
