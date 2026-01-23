# Plan: Fix Graphite Stack Metadata (Option C)

## Problem

`erk plan submit` creates PRs via `gh pr create` (GitHub REST API), not `gt submit`, so Graphite's remote stack metadata is never established. Users must manually run `erk pr sync --dangerous` after checkout to integrate branches with Graphite.

## Solution

**Option C**: Fix at BOTH submit time AND checkout time for defense-in-depth.

---

## Part A: Fix at Submit Time

### Files to Modify

- `src/erk/cli/commands/submit.py`

### Changes

**Path 1: `_create_branch_and_pr()` - Insert after line 399, before line 400**

After the learn label logic and before closing orphaned PRs:

```python
# Link PR with Graphite (if enabled)
if ctx.branch_manager.is_graphite_managed():
    user_output("Linking PR with Graphite...")
    ctx.branch_manager.submit_branch(repo.root, branch_name)
    user_output(click.style("✓", fg="green") + " PR linked with Graphite")
```

**Path 2: `_submit_single_issue()` existing branch path - Insert after line 514, before line 515**

Same pattern - after learn label, before closing orphaned PRs:

```python
# Link PR with Graphite (if enabled)
if ctx.branch_manager.is_graphite_managed():
    user_output("Linking PR with Graphite...")
    ctx.branch_manager.submit_branch(repo.root, branch_name)
    user_output(click.style("✓", fg="green") + " PR linked with Graphite")
```

**Rationale**: Must happen BEFORE restoring local state (lines 409-413 and 524-527) because the branch gets deleted after.

---

## Part B: Fix at Checkout Time

### Files to Modify

- `src/erk/cli/commands/pr/checkout_cmd.py`

### Changes

**Insert after line 159, before line 161** (after stacked PR rebase handling, before `navigate_and_display_checkout`):

```python
# Graphite integration: Track and submit if enabled (for new worktrees only)
if (
    ctx.branch_manager.is_graphite_managed()
    and not already_existed
    and not pr.is_cross_repository
):
    parent = ctx.branch_manager.get_parent_branch(repo.root, branch_name)
    if parent is None:
        ctx.console.info("Tracking branch with Graphite...")
        ctx.branch_manager.track_branch(worktree_path, branch_name, pr.base_ref_name)
        ctx.console.info("Submitting to link with Graphite...")
        ctx.branch_manager.submit_branch(worktree_path, branch_name)
        ctx.console.info(click.style("✓", fg="green") + " Branch linked with Graphite")
```

**Design decisions:**
- Only for new worktrees (`not already_existed`) - existing worktrees may already be tracked
- Skip for fork PRs (`not pr.is_cross_repository`) - can't track cross-repo branches
- Check if already tracked (`parent is None`) - idempotent
- Use `worktree_path` for operations - branch is checked out there

---

## Testing Strategy

### New Test File: `tests/commands/plan/test_submit_graphite_linking.py`

1. `test_plan_submit_links_pr_with_graphite_when_enabled` - verify `submit_branch` called
2. `test_plan_submit_skips_graphite_when_disabled` - no `submit_branch` calls
3. `test_plan_submit_existing_branch_links_with_graphite` - Path 2 coverage

### New Test File: `tests/commands/pr/test_checkout_graphite_linking.py`

1. `test_pr_checkout_tracks_and_submits_with_graphite` - verify both calls
2. `test_pr_checkout_skips_graphite_for_existing_worktree` - idempotent
3. `test_pr_checkout_skips_graphite_for_already_tracked` - idempotent
4. `test_pr_checkout_skips_graphite_for_fork_prs` - cross-repo handling

---

## Verification

1. Run existing tests: `make fast-ci`
2. Manual test with Graphite enabled:
   - `erk plan submit` a stacked plan
   - Verify `gt log` shows the PR in Graphite's metadata
   - `erk pr checkout <pr-number>` in a fresh worktree
   - Verify `gt log` shows proper stack tracking
3. Manual test with Graphite disabled:
   - Same flow should work without Graphite errors

---

## Critical Files

| File | Purpose |
|------|---------|
| `src/erk/cli/commands/submit.py:399` | Path 1 insertion point |
| `src/erk/cli/commands/submit.py:514` | Path 2 insertion point |
| `src/erk/cli/commands/pr/checkout_cmd.py:159` | Checkout insertion point |
| `packages/erk-shared/src/erk_shared/branch_manager/fake.py` | Test assertions |
| `src/erk/cli/commands/pr/sync_cmd.py:280` | Reference implementation |

---

## Related Documentation

- `fake-driven-testing` skill for test architecture
- `dignified-python` skill for code standards