# Plan: Phase 3 - Unify Entry Points in `erk land`

**Part of Objective #5466, Phase 3 (Steps 3.1-3.7)**

## Goal

Refactor the three entry points (`_land_current_branch`, `_land_specific_pr`, `_land_by_branch`) into thin resolvers that delegate to a shared validation + script-generation path via a `LandTarget` dataclass and unified `_land_target()` function.

## Related Documentation

- Skills to load: `dignified-python` (loaded), `fake-driven-testing` (loaded)
- Tripwires: frozen dataclasses required, no default parameter values, LBYL patterns

## Current State

Three entry points with ~80% duplicated validation logic:
- `_land_current_branch()` (lines 1257-1427): 170 lines
- `_land_specific_pr()` (lines 1430-1568): 138 lines
- `_land_by_branch()` (lines 1571-1701): 130 lines

**Shared across all three** (~80% duplication):
- PR state validation (OPEN check)
- Unresolved comments check
- Learn status check
- Objective lookup
- Slot assignment lookup
- Dry-run output
- Script generation + writing + display

**Unique per entry point:**
- `_land_current_branch`: Graphite stack validation, `--up` flag handling, mandatory worktree, `use_graphite=True`
- `_land_specific_pr`: `--up` rejection, fork PR branch resolution, nullable worktree, `use_graphite=False`
- `_land_by_branch`: Branch from parameter, nullable worktree, `use_graphite=False`, no `--up` support

## Design

### Step 3.1: Create `LandTarget` dataclass

A frozen dataclass that carries all resolved landing state from a resolver to the unified flow.

```python
@dataclass(frozen=True)
class LandTarget:
    """Resolved landing target from any entry point."""
    branch: str
    pr_details: PRDetails
    worktree_path: Path | None
    is_current_branch: bool
    use_graphite: bool
    target_child_branch: str | None  # Only set for --up mode
```

Place in `land_cmd.py` alongside `CleanupContext`.

### Step 3.2: Create `_validate_pr_for_landing()` shared function

Extracts the common validation steps that happen after PR resolution:

```python
def _validate_pr_for_landing(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    target: LandTarget,
    force: bool,
    script: bool,
) -> None:
```

This function validates:
1. Clean working tree (if `is_current_branch`)
2. PR state is OPEN
3. PR base is trunk (for non-Graphite paths; Graphite path validates via stack)
4. Unresolved comments check
5. Learn status check (for plan branches with worktrees)

Raises `SystemExit(1)` on validation failure.

### Steps 3.3-3.5: Create three resolver functions

Each resolver becomes thin (15-30 lines) and returns a `LandTarget`:

**`_resolve_land_target_current_branch()`** - Resolves current branch, validates `--up` preconditions, validates Graphite stack, looks up PR by branch. Returns `LandTarget(use_graphite=True/False based on branch_manager)`.

**`_resolve_land_target_pr()`** - Fetches PR by number, resolves branch (handles forks), determines worktree. Rejects `--up`. Returns `LandTarget(use_graphite=False)`.

**`_resolve_land_target_branch()`** - Looks up PR by branch name, determines worktree. Returns `LandTarget(use_graphite=False)`.

### Step 3.6: Create unified `_land_target()`

After a resolver returns a `LandTarget`, this function handles everything else:

```python
def _land_target(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    target: LandTarget,
    script: bool,
    force: bool,
    pull_flag: bool,
    no_delete: bool,
) -> None:
```

Flow:
1. Call `_validate_pr_for_landing(ctx, repo=repo, target=target, force=force, script=script)`
2. Look up objective: `get_objective_for_branch(ctx, main_repo_root, target.branch)`
3. Look up slot assignment: `load_pool_state()` + `find_branch_assignment()`
4. Determine target_path (child worktree if `--up`, else main_repo_root)
5. Handle dry-run output
6. Generate + write execution script
7. Display instructions / output path

### Step 3.7: Simplify entry points to resolve -> validate -> land

The `land()` Click command becomes:

```python
if target is None:
    land_target = _resolve_land_target_current_branch(ctx, repo=repo, up_flag=up_flag)
elif parsed.arg_type == "branch":
    land_target = _resolve_land_target_branch(ctx, repo=repo, branch_name=target)
else:
    land_target = _resolve_land_target_pr(ctx, repo=repo, pr_number=pr_number, up_flag=up_flag)

_land_target(ctx, repo=repo, target=land_target, script=script, force=force, pull_flag=pull_flag, no_delete=no_delete)
```

## Implementation Phases

### Phase A: Create dataclass + shared validation (Steps 3.1 + 3.2)

1. Add `LandTarget` frozen dataclass to `land_cmd.py`
2. Create `_validate_pr_for_landing()` that consolidates shared validation
3. Add unit tests for `_validate_pr_for_landing()` covering:
   - PR not open -> fails
   - PR base not trunk -> fails (non-Graphite mode)
   - Unresolved comments -> prompts (when not forced)
   - Learn status check (plan branch with worktree)
   - Clean working tree check (when is_current_branch)

### Phase B: Create resolvers (Steps 3.3-3.5)

4. Create `_resolve_land_target_current_branch()` resolver
5. Create `_resolve_land_target_pr()` resolver
6. Create `_resolve_land_target_branch()` resolver
7. Add unit tests for each resolver covering:
   - Current branch: Graphite validation, --up child resolution
   - Specific PR: fork branch resolution, --up rejection
   - Branch: PR lookup by name

### Phase C: Create unified flow + simplify entry points (Steps 3.6-3.7)

8. Create `_land_target()` unified function
9. Refactor `land()` Click command to use resolve -> land pattern
10. Remove old `_land_current_branch()`, `_land_specific_pr()`, `_land_by_branch()` functions
11. Run full land test suite to verify no regressions

## Files to Modify

- `src/erk/cli/commands/land_cmd.py` (primary - add LandTarget, resolvers, unified flow, remove old functions)
- `tests/unit/cli/commands/land/` (new test files for LandTarget, _validate_pr_for_landing, resolvers)

## Behavioral Preservation Notes

- `_land_current_branch` validates Graphite stack BEFORE PR lookup, while the other two validate PR base directly. The unified `_validate_pr_for_landing()` must handle both paths: skip base-is-trunk check when `use_graphite=True` (Graphite already validated in resolver).
- `_land_current_branch` always checks learn status (even without worktree - though it always has one). The other two only check when `worktree_path is not None`. The unified function should use: check learn status when `plan_issue_number is not None and (target.is_current_branch or target.worktree_path is not None)`.
- Error message for PR-not-open differs slightly between current-branch (includes "has already been {state}") and specific-PR/branch (simpler). Unify to the more informative message.
- Error message for PR-base-mismatch includes different retry hints: `erk land {pr_number}` vs `erk land {branch_name}`. The unified function can use the branch name since all targets carry `target.branch`.
- Script instruction text differs: "To land the PR:" vs "To land PR #N:" vs "To land branch 'X':". The unified function can derive this from the target type.

## Test Strategy

- **New unit tests** for `LandTarget`, `_validate_pr_for_landing()`, and each resolver (Layer 4 - over fakes)
- **Existing tests pass unchanged** - all tests in `tests/commands/land/` and `tests/unit/cli/commands/land/` must continue passing
- Run: `pytest tests/commands/land/ tests/unit/cli/commands/land/ tests/unit/cli/commands/exec/scripts/test_land_execute.py`

## Verification

1. Run land test suite: `pytest tests/commands/land/ tests/unit/cli/commands/land/ tests/unit/cli/commands/exec/scripts/`
2. Run type checker: `ty check src/erk/cli/commands/land_cmd.py`
3. Run linter: `ruff check src/erk/cli/commands/land_cmd.py`
4. Verify line count reduction: old ~440 lines for 3 functions -> target ~200 lines for resolvers + unified flow