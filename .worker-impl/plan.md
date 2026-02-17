# Add --up option to erk stack consolidate

## Context

`erk stack consolidate` currently supports two modes:
- **Full stack (default)**: Consolidates all branches from trunk to leaf
- **`--down`**: Consolidates only downstack branches (trunk to current branch)

The missing mode is **`--up`**: consolidate only upstack branches (current branch to leaf), leaving downstack worktrees untouched. This is useful when you want to work on the upper portion of a stack without disturbing lower worktrees.

The `--up` and `--down` flags must be mutually exclusive. The `BRANCH` positional argument should also be incompatible with `--up` (same as `--down`).

## Design

### How --down works (pattern to follow)

The `--down` flag works by setting `end_branch = current_branch`, which causes `calculate_stack_range()` to return branches from trunk up to (and including) the current branch. This is a slice from the front of the stack list.

### How --up will work

`--up` needs the **opposite** slice: branches from the current branch to the leaf. This requires a new function `calculate_upstack_range()` since the existing `calculate_stack_range()` always slices from the start (trunk) to an endpoint.

**Stack layout**: `['main', 'feat-1', 'feat-2', 'feat-3']`
- Full stack: `['main', 'feat-1', 'feat-2', 'feat-3']`
- `--down` (current=feat-2): `['main', 'feat-1', 'feat-2']`
- `--up` (current=feat-2): `['feat-2', 'feat-3']`

Note: `--up` includes the current branch in the consolidation range. This is symmetric with `--down` which also includes the current branch. Including the current branch means that worktrees for the current branch's siblings (if any exist in separate worktrees) will be consolidated. The current worktree itself is always preserved (never removed).

## Changes

### 1. `src/erk/core/consolidation_utils.py`

Add a new pure function `calculate_upstack_range()`:

```python
def calculate_upstack_range(
    stack_branches: list[str],
    start_branch: str,
) -> list[str]:
    """Calculate upstack portion of the stack to consolidate.

    Args:
        stack_branches: Full stack from trunk to leaf
        start_branch: Branch to start from (inclusive)

    Returns:
        List of branches from start_branch to leaf (inclusive).

    Raises:
        ValueError: If start_branch is not in stack_branches
    """
    if start_branch not in stack_branches:
        raise ValueError(f"Branch '{start_branch}' not in stack")

    branch_index = stack_branches.index(start_branch)
    return stack_branches[branch_index:]
```

Update `create_consolidation_plan()` to accept a `start_branch` parameter alongside `end_branch`:

```python
def create_consolidation_plan(
    *,
    all_worktrees: list[WorktreeInfo],
    stack_branches: list[str],
    end_branch: str | None,
    start_branch: str | None = None,
    target_worktree_path: Path,
    source_worktree_path: Path | None = None,
) -> ConsolidationPlan:
```

The logic inside: if `start_branch` is provided, use `calculate_upstack_range(stack_branches, start_branch)` instead of `calculate_stack_range(stack_branches, end_branch)`.

`start_branch` and `end_branch` should be treated as mutually exclusive at this level (caller ensures this).

### 2. `src/erk/cli/commands/stack/consolidate_cmd.py`

**Add the `--up` Click option** (after the `--down` option, around line 141):

```python
@click.option(
    "--up",
    "up",
    is_flag=True,
    help="Only consolidate upstack (current branch to leaf). Default is entire stack.",
)
```

**Update function signature** to include `up: bool`.

**Add mutual exclusivity validation** (after the existing `--down` + BRANCH validation, around line 206):

```python
# Validate that --up and --down are not used together
if up and down:
    user_output(click.style("Error: Cannot use --up with --down", fg="red"))
    user_output("Use either --up (consolidate current to leaf) or --down (consolidate trunk to current)")
    raise SystemExit(1)

# Validate that --up and BRANCH are not used together
if up and branch is not None:
    user_output(click.style("Error: Cannot use --up with BRANCH argument", fg="red"))
    user_output(
        "Use either --up (consolidate current to leaf) or "
        "BRANCH (consolidate trunk to BRANCH)"
    )
    raise SystemExit(1)
```

**Update the stack range calculation** (around lines 261-264):

```python
# Calculate stack range early (needed for safety check)
if up:
    start_branch = current_branch
    end_branch = None
    stack_to_consolidate = calculate_upstack_range(stack_branches, start_branch)
elif down:
    start_branch = None
    end_branch = current_branch
    stack_to_consolidate = calculate_stack_range(stack_branches, end_branch)
else:
    start_branch = None
    end_branch = branch
    stack_to_consolidate = calculate_stack_range(stack_branches, end_branch)
```

**Update the `create_consolidation_plan()` call** (around line 353) to pass `start_branch`:

```python
plan = create_consolidation_plan(
    all_worktrees=all_worktrees,
    stack_branches=stack_branches,
    end_branch=end_branch,
    start_branch=start_branch if up else None,
    target_worktree_path=target_worktree_path,
    source_worktree_path=current_worktree if name is not None else None,
)
```

**Update the help text/docstring** to mention `--up`:

Add to the docstring:
- Description: "With --up, consolidates only upstack branches (current to leaf)."
- Example: `$ erk consolidate --up`

### 3. `tests/core/utils/test_consolidation_utils.py`

Add tests for `calculate_upstack_range()`:

- `test_upstack_range_from_middle_branch`: Starting from `feat-2` in `['main', 'feat-1', 'feat-2', 'feat-3']` returns `['feat-2', 'feat-3']`
- `test_upstack_range_from_first_branch`: Starting from `main` returns full stack
- `test_upstack_range_from_last_branch`: Starting from `feat-3` returns `['feat-3']`
- `test_upstack_range_error_when_branch_not_in_stack`: Starting from `'unknown'` raises `ValueError`
- `test_upstack_range_single_branch_stack`: Stack of `['main']`, start from `main` returns `['main']`

Add tests for `create_consolidation_plan()` with `start_branch`:

- `test_upstack_consolidation_plan`: Verify plan correctly filters worktrees using upstack range

### 4. `tests/commands/workspace/test_consolidate.py`

Add integration tests:

- `test_consolidate_up_removes_only_upstack_worktrees`: With stack `main -> feat-1 -> feat-2 -> feat-3`, current on `feat-2`, `--up` should only remove `feat-3` worktree (not `main` or `feat-1`)
- `test_consolidate_up_and_down_mutually_exclusive`: Using both `--up` and `--down` should fail with error message
- `test_consolidate_up_and_branch_mutually_exclusive`: Using `--up` with BRANCH argument should fail
- `test_consolidate_up_dry_run`: Verify `--up --dry-run` shows correct preview without executing
- `test_consolidate_up_no_upstack_worktrees`: When current is the leaf, `--up` should say "No other worktrees found"

## Files NOT Changing

- `src/erk/cli/commands/stack/__init__.py` - No registration changes needed
- `src/erk/cli/help_formatter.py` - No formatter changes
- `src/erk/cli/activation.py` - Not affected
- `tests/commands/stack/test_consolidate_cmd.py` - Graphite/slot-level tests not affected
- `CHANGELOG.md` - Never modified in plans

## Verification

1. Run unit tests: `pytest tests/core/utils/test_consolidation_utils.py -v`
2. Run integration tests: `pytest tests/commands/workspace/test_consolidate.py -v`
3. Run stack command tests: `pytest tests/commands/stack/test_consolidate_cmd.py -v`
4. Run type checker: `ty check src/erk/core/consolidation_utils.py src/erk/cli/commands/stack/consolidate_cmd.py`
5. Run linter: `ruff check src/erk/core/consolidation_utils.py src/erk/cli/commands/stack/consolidate_cmd.py`

## Implementation Notes

- Follow LBYL pattern (no try/except for control flow)
- Use frozen dataclasses (already established pattern)
- Pure functions for business logic in `consolidation_utils.py`
- The `--up` flag name uses `"up"` as the dest parameter to avoid Python keyword conflict (Click handles this)
- Import `calculate_upstack_range` in `consolidate_cmd.py` alongside existing `calculate_stack_range`