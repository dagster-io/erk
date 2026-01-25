---
title: Multi-Entry-Point Commands
read_when:
  - "designing CLI commands with multiple input types"
  - "unifying PR number, branch name, and current context entry points"
  - "understanding LandTarget and CleanupContext patterns"
  - "refactoring commands to support multiple argument forms"
---

# Multi-Entry-Point Commands

Pattern for CLI commands that accept multiple argument types (PR number, branch name, URL, or current context) while maintaining a single downstream code path.

## Problem

Commands like `erk land` need to accept:

- No argument (use current branch)
- PR number (`erk land 456`)
- PR URL (`erk land https://github.com/owner/repo/pull/456`)
- Branch name (`erk land feature-branch`)

Without unification, this leads to duplicated logic or parameter explosion in downstream functions.

## Solution: Frozen Dataclass + Resolver Pattern

Use a frozen dataclass as "common currency" that all entry points resolve to, enabling a single downstream code path.

### 1. Define the Target Dataclass

```python
@dataclass(frozen=True)
class LandTarget:
    """Resolved landing target from any entry point."""
    branch: str
    pr_details: PRDetails
    worktree_path: Path | None
    is_current_branch: bool
    use_graphite: bool
    target_child_branch: str | None
```

This dataclass captures everything downstream code needs, regardless of how the user specified the target.

### 2. Create Thin Resolver Functions

Each resolver handles one entry point type and returns the common type:

```python
def _resolve_land_target_current_branch(
    ctx: ErkContext, *, repo: RepoContext, up_flag: bool
) -> LandTarget:
    """Resolve target when no argument provided (current branch)."""
    # Entry-point-specific logic here
    return LandTarget(...)

def _resolve_land_target_pr(
    ctx: ErkContext, *, repo: RepoContext, pr_number: int, up_flag: bool
) -> LandTarget:
    """Resolve target from PR number or URL."""
    return LandTarget(...)

def _resolve_land_target_branch(
    ctx: ErkContext, *, repo: RepoContext, branch_name: str
) -> LandTarget:
    """Resolve target from branch name."""
    return LandTarget(...)
```

### 3. Dispatch in Main Command

```python
@click.command()
@click.argument("target", required=False)
def land(target: str | None) -> None:
    if target is None:
        land_target = _resolve_land_target_current_branch(...)
    else:
        parsed = parse_argument(target)
        if parsed.arg_type == "branch":
            land_target = _resolve_land_target_branch(...)
        else:
            land_target = _resolve_land_target_pr(...)

    # Single downstream flow for all entry points
    _land_target(ctx, repo=repo, target=land_target, ...)
```

## Bundling Parameters with Context Dataclasses

When downstream functions need many parameters, bundle them into a frozen dataclass:

```python
@dataclass(frozen=True)
class CleanupContext:
    """Carries cleanup state through the extraction process."""
    ctx: ErkContext
    repo: RepoContext
    branch: str
    worktree_path: Path | None
    is_current_branch: bool
    plan_issue_number: int | None
    target_child_branch: str | None
    use_graphite: bool
    force: bool
    up_flag: bool
```

Benefits:

- Prevents parameter explosion (10+ parameters per function)
- Self-documenting field names
- Thread-safe passing between functions
- Enables `dataclasses.replace()` for creating modified copies

## Argument Parsing Helper

Use a helper to classify argument types:

```python
@dataclass(frozen=True)
class ParsedArgument:
    arg_type: Literal["pr_number", "pr_url", "branch"]
    value: str | int

def parse_argument(arg: str) -> ParsedArgument:
    """Classify argument as PR number, PR URL, or branch name."""
    if arg.isdigit():
        return ParsedArgument(arg_type="pr_number", value=int(arg))
    if "github.com" in arg and "/pull/" in arg:
        return ParsedArgument(arg_type="pr_url", value=arg)
    return ParsedArgument(arg_type="branch", value=arg)
```

## Benefits

1. **Single downstream path** - All entry points converge to one implementation
2. **Type safety** - Frozen dataclass ensures all fields are populated
3. **Testability** - Each resolver can be tested independently
4. **Maintainability** - New entry points only require new resolver
5. **Documentation** - Dataclass fields document what downstream code needs

## Canonical Implementation

See `src/erk/cli/commands/land_cmd.py` for the complete pattern:

- `LandTarget` dataclass (common currency)
- `CleanupContext` dataclass (parameter bundling)
- Three resolver functions (`_resolve_land_target_*`)
- Single downstream function (`_land_target`)

## Related Topics

- [Resolver Pattern](resolver-pattern.md) - Detailed resolver function patterns
- [Frozen Dataclass Patterns](../architecture/frozen-dataclass-patterns.md) - Frozen dataclass usage guidelines
