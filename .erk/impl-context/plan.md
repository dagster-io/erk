# Fix: `erk pr teleport` doesn't register branch with Graphite for non-stacked PRs

## Context

After `erk pr teleport`, running `gt submit` fails because Graphite doesn't know about the branch. The user must manually run `gt track` and `gt get` to sync state. Teleport should leave the branch fully ready for Graphite operations.

**Root cause:** `_reconstruct_graphite_stack` in `teleport_cmd.py:213` has an early return when `base_ref_name == trunk`, skipping ALL Graphite registration for non-stacked PRs. Compare with `checkout_cmd.py:303` which correctly calls `track_branch` for all PRs.

## Changes

### File: `src/erk/cli/commands/pr/teleport_cmd.py`

1. **Rename** `_reconstruct_graphite_stack` → `_register_with_graphite` (the function isn't just for stacks)

2. **Restructure** the function to always run track/retrack, gating only the base-branch-fetch on stacked PRs:

```python
def _register_with_graphite(ctx, repo, *, branch_name, base_ref_name):
    if not ctx.branch_manager.is_graphite_managed():
        return

    trunk = ctx.git.branch.detect_trunk_branch(repo.root)

    # For stacked PRs, ensure base branch exists locally
    if base_ref_name != trunk:
        local_branches = ctx.git.branch.list_local_branches(repo.root)
        if base_ref_name not in local_branches:
            ctx.console.info(f"Fetching base branch '{base_ref_name}'...")
            ctx.git.remote.fetch_branch(repo.root, "origin", base_ref_name)
            ctx.branch_manager.create_tracking_branch(
                repo.root, base_ref_name, f"origin/{base_ref_name}"
            )

    # Always register/retrack with Graphite
    parent = ctx.branch_manager.get_parent_branch(repo.root, branch_name)
    if parent is None:
        ctx.console.info("Tracking branch with Graphite...")
        ctx.branch_manager.track_branch(repo.root, branch_name, base_ref_name)
    else:
        if ctx.graphite_branch_ops is not None:
            ctx.graphite_branch_ops.retrack_branch(repo.root, branch_name)
```

3. **Update** both call sites (lines 151, 183) to use the new name.

## Verification

- Run existing teleport tests to ensure no regressions
- Check if there are tests covering the Graphite registration path for non-stacked PRs; add one if not
