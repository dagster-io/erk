# Fix: erk pr sync missing push + pr-address wrong push command

## Context

When `erk pr sync --dangerous` runs on an **already-tracked** Graphite branch, it syncs and restacks locally but never pushes the result back to remote. This causes a local/remote SHA divergence. When `pr-address` later commits changes and runs `git push`, it fails with a non-fast-forward error — triggering a messy rebase/retrack recovery flow.

The root cause is a missing `submit_branch()` call in the "already tracked" code path. A defense-in-depth fix is also needed in `pr-address.md` which currently tells Claude to use `git push` instead of `gt submit` for Graphite repos.

## Fix 1: `sync_cmd.py` — Add push to "already tracked" path

**File:** `src/erk/cli/commands/pr/sync_cmd.py`

The "already tracked" path (lines 222-257) currently ends with:
```python
        user_output(click.style("✓", fg="green") + " Branch restacked")
        # Auto-fix tracking divergence...
        if ...:
            ctx.graphite_branch_ops.retrack_branch(...)
        return  # ← no push!
```

**Change:** Before the `return`, add the same `submit_branch()` call used by the first-time path (lines 322-328):

```python
        # Push restacked branch to remote
        user_output("Pushing to remote...")
        submit_result = ctx.branch_manager.submit_branch(repo.root, current_branch)
        if isinstance(submit_result, SubmitBranchError):
            raise click.ClickException(f"Failed to push: {submit_result.message}")
        user_output(click.style("✓", fg="green") + " Pushed to remote")
        return
```

`submit_branch()` is idempotent (uses `--force`) — safe to call even when restack was a no-op.

Also need to add the import for `SubmitBranchError` if not already imported (it is — line 37).

## Fix 2: `pr-address.md` — Use correct push command for Graphite

**File:** `.claude/commands/erk/pr-address.md`

Lines 247-249 currently say:
```
1. Push changes: `git push`
   - If push is rejected (non-fast-forward): Run `/erk:sync-divergence`
```

**Change:** Follow the same pattern used in `fix-conflicts.md` — branch on Graphite vs plain git:

```
1. Push changes:
   - **Graphite repos**: `gt submit` (or `gt ss`)
   - **Plain git repos**: `git push`
   - If push is rejected (non-fast-forward): Run `/erk:sync-divergence` to resolve. Do NOT use `git pull --rebase`.
```

This matches the existing pattern in `.claude/commands/erk/fix-conflicts.md` and `.claude/commands/erk/sync-divergence.md`.

## Fix 3: Update existing test

**File:** `tests/commands/pr/test_sync.py`

Test `test_pr_sync_syncs_remote_when_already_tracked` (line 133) explicitly asserts the old behavior — no push:
```python
assert len(graphite.submit_stack_calls) == 0  # line 187
```

**Change:** Flip this assertion to verify push now happens:
```python
assert len(graphite.submit_stack_calls) == 1
```

Also verify the output includes the new push messaging.

## Files to modify

1. `src/erk/cli/commands/pr/sync_cmd.py` — Add submit_branch() call before the return on line 257
2. `.claude/commands/erk/pr-address.md` — Update push instructions (lines 247-249)
3. `tests/commands/pr/test_sync.py` — Update assertion on line 187 from 0 to 1

## Verification

1. Run `pytest tests/commands/pr/test_sync.py` — all sync tests pass, including the updated assertion
2. Run `make fast-ci` to ensure nothing else breaks