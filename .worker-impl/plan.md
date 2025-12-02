# Fix: erk implement should preserve Graphite stacking from current branch

## Problem

When running `erk implement` from within a worktree (e.g., `1938-clickable-local-worktree-c-12-02-1103`), the new branch is NOT stacked on top of the current branch. Instead, it's always stacked on trunk (main/master).

**Expected**: `1944-...` should be stacked on `1938-...` (preserving the stack)
**Actual**: `1944-...` is stacked on `main` (breaking the stack)

## Design Decision

Stack on current branch **only when Graphite is enabled** (`use_graphite=True`). Without Graphite, continue using trunk as the base branch (current behavior).

## Root Cause

Two locations hardcode `trunk_branch` as the base:

### 1. `implement.py:363-374` - Branch creation via GitHub

```python
trunk_branch = ctx.git.detect_trunk_branch(repo_root)  # Always trunk
...
dev_branch = ctx.issue_link_branches.create_development_branch(
    ...
    base_branch=trunk_branch,  # ALWAYS trunk!
)
```

### 2. `implement.py:573-582` - Worktree creation

```python
add_worktree(
    ...
    ref=trunk_branch,  # Also always trunk!
)
```

### 3. `create_cmd.py:264-269` - Graphite tracking for existing branches

```python
ctx.graphite.track_branch(path, branch, ref)  # ref=trunk_branch from caller
```

## Implementation

### Step 1: Add helper function to determine base branch (`implement.py`)

Add a new helper function that encapsulates the stacking logic:

```python
def _determine_base_branch(ctx: ErkContext, repo_root: Path) -> str:
    """Determine the base branch for new worktree creation.

    When Graphite is enabled and the user is on a non-trunk branch,
    stack on the current branch. Otherwise, use trunk.
    """
    trunk_branch = ctx.git.detect_trunk_branch(repo_root)
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False

    if not use_graphite:
        return trunk_branch

    current_branch = ctx.git.get_current_branch(ctx.cwd)
    if current_branch and current_branch != trunk_branch:
        return current_branch

    return trunk_branch
```

### Step 2: Update `_implement_from_issue()` to use helper

```python
def _implement_from_issue(...):
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)

    # Determine base branch (respects Graphite stacking)
    base_branch = _determine_base_branch(ctx, repo.root)

    issue_plan_source = _prepare_plan_source_from_issue(
        ctx, repo.root, issue_number, base_branch=base_branch
    )

    wt_path = _create_worktree_with_plan_content(
        ctx,
        plan_source=issue_plan_source.plan_source,
        ...
        base_branch=base_branch,  # NEW parameter
    )
```

### Step 3: Update `_implement_from_file()` similarly

```python
def _implement_from_file(...):
    repo = discover_repo_context(ctx, ctx.cwd)
    base_branch = _determine_base_branch(ctx, repo.root)

    plan_source = _prepare_plan_source_from_file(ctx, plan_file)

    wt_path = _create_worktree_with_plan_content(
        ctx,
        plan_source=plan_source,
        ...
        base_branch=base_branch,  # NEW parameter
    )
```

### Step 4: Update `_prepare_plan_source_from_issue()` signature

Add `base_branch` parameter and pass it to `create_development_branch()`:

```python
def _prepare_plan_source_from_issue(
    ctx: ErkContext,
    repo_root: Path,
    issue_number: str,
    base_branch: str,  # NEW parameter
) -> IssuePlanSource:
    ...
    dev_branch = ctx.issue_link_branches.create_development_branch(
        repo_root,
        int(issue_number),
        branch_name=desired_branch_name,
        base_branch=base_branch,  # Was: trunk_branch
    )
```

### Step 5: Update `_create_worktree_with_plan_content()` signature

Add `base_branch` parameter (replaces internal `trunk_branch` usage):

```python
def _create_worktree_with_plan_content(
    ctx: ErkContext,
    *,
    plan_source: PlanSource,
    ...
    base_branch: str,  # NEW parameter (replaces internal trunk_branch)
) -> Path | None:
    ...
    # Use base_branch instead of trunk_branch for validation and add_worktree
    if not use_existing_branch:
        ...  # validation logic unchanged

    add_worktree(
        ctx,
        repo_root,
        wt_path,
        branch=branch,
        ref=base_branch,  # Was: trunk_branch
        ...
    )
```

## Files to Modify

1. `/Users/schrockn/code/erk/src/erk/cli/commands/implement.py`
   - Add `_determine_base_branch()` helper function
   - Update `_implement_from_issue()` to compute and pass `base_branch`
   - Update `_implement_from_file()` to compute and pass `base_branch`
   - Update `_prepare_plan_source_from_issue()` to accept `base_branch` parameter
   - Update `_create_worktree_with_plan_content()` to accept `base_branch` parameter

2. No changes needed to `create_cmd.py` - it already handles `ref` correctly

## Testing

Add tests in `tests/commands/test_implement.py`:

### Test 1: Graphite enabled, on non-trunk branch - stacks on current

```python
def test_implement_from_worktree_stacks_on_current_branch_with_graphite() -> None:
    """When Graphite enabled and on feature branch, stack on current branch."""
    plan_issue = _create_sample_plan_issue("123")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},  # On feature branch
        )
        store = FakePlanStore(plans={"123": plan_issue})
        issue_dev = FakeIssueLinkBranches()
        ctx = env.build_context(
            git=git,
            plan_store=store,
            issue_link_branches=issue_dev,
            use_graphite=True,  # Graphite enabled
        )

        result = runner.invoke(implement, ["123", "--script"], obj=ctx)

        assert result.exit_code == 0
        # Verify branch was created with feature-branch as base
        assert issue_dev.create_calls[0].base_branch == "feature-branch"
```

### Test 2: Graphite disabled, on non-trunk branch - uses trunk

```python
def test_implement_from_worktree_uses_trunk_without_graphite() -> None:
    """When Graphite disabled, always use trunk as base even if on feature branch."""
    # Similar setup but use_graphite=False
    # Assert issue_dev.create_calls[0].base_branch == "main"
```

### Test 3: Graphite enabled, on trunk - uses trunk

```python
def test_implement_from_trunk_uses_trunk_with_graphite() -> None:
    """When on trunk branch, use trunk as base regardless of Graphite."""
    # Setup with current_branches={env.cwd: "main"}
    # Assert issue_dev.create_calls[0].base_branch == "main"
```
