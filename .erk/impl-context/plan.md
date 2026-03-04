# Fix `erk down -d` for same-worktree downstack navigation

## Context

When `erk br co --for-plan` checks out a new plan branch into an existing worktree (rather than creating a new one), the new branch and its parent share the same physical worktree directory. Running `erk down -d -f` in this scenario:

1. Detects `same_worktree=True` (target path == current worktree path)
2. Closes the PR (correct)
3. **Shows `erk br delete {branch} -f`** as the suggested command (wrong)

Running the suggested `erk br delete` then:
1. Finds the worktree for the branch (the shared worktree)
2. Deletes the worktree
3. **Crashes** trying to run `gt is_branch_tracked` with `cwd` pointing to the now-deleted worktree

There are two bugs to fix.

---

## Bug A: Wrong deletion command suggested by `erk down -d` in same-worktree case

**File:** `src/erk/cli/commands/navigation_helpers.py`

**Location:** `_activate_with_deferred_deletion()` (~line 890)

**Current behavior** (non-script path, `same_worktree=True`, `force=True`):
- Calls `print_activation_instructions(..., source_branch=current_branch, force=True, same_worktree=True)`
- `print_activation_instructions` generates: `erk br delete {branch} -f`
- This is wrong: `erk br delete` will try to delete the worktree which belongs to the downstack branch

**Fix:** When `same_worktree=True` and `deletion_commands` is not None:

1. **Filter deletion_commands** to exclude worktree/slot removal — the worktree belongs to the downstack (target) branch and must not be removed:
   ```python
   if same_worktree and deletion_commands:
       deletion_commands = [
           cmd for cmd in deletion_commands
           if not cmd.startswith("git worktree remove")
           and not cmd.startswith("erk slot unassign")
       ]
   ```

2. **In non-script mode with `same_worktree=True`**, show the actual commands directly (checkout + branch delete) instead of `erk br delete`:
   - Don't pass `source_branch` to `print_activation_instructions` (avoids the `erk br delete` hint)
   - Instead display the filtered `deletion_commands` joined as: `git checkout {parent} && gt delete -f --no-interactive {branch}`

3. **In script mode with `same_worktree=True`**, the filtered `deletion_commands` (no worktree remove) are correctly embedded in the activation script already — this path works after the filter is applied.

---

## Bug B: `erk br delete` crash after worktree deletion

**File:** `src/erk/cli/commands/branch/delete_cmd.py`

**Location:** `_delete_branch()` (~line 280)

**Root cause:** `repo` is discovered at line 280 with `repo.root` = worktree path. After `_handle_vanilla_worktree()` (line 318) deletes the worktree and escapes cwd to `main_repo_root`, `repo` is stale — `repo.root` still points to the deleted directory. Subsequent calls to `_close_pr_for_branch(ctx, repo.root, ...)` and `_delete_branch_at_error_boundary(ctx, repo_root=repo.root, ...)` fail with `FileNotFoundError`.

**Fix:** Re-discover `repo` after `_handle_vanilla_worktree` returns:
```python
elif wt_info.has_worktree:
    ctx = _handle_vanilla_worktree(ctx, repo, wt_info, dry_run)
    if not dry_run:
        repo = discover_repo_context(ctx, ctx.cwd)  # cwd now points to main_repo_root
```

This ensures all subsequent operations use a valid, existing cwd.

---

## Files to Modify

1. **`src/erk/cli/commands/navigation_helpers.py`** — `_activate_with_deferred_deletion()`:
   - Filter `deletion_commands` when `same_worktree=True` (remove worktree/slot removal)
   - In non-script mode with `same_worktree=True` + `deletion_commands`: show the filtered commands directly instead of delegating to `print_activation_instructions` with `source_branch`

2. **`src/erk/cli/commands/branch/delete_cmd.py`** — `_delete_branch()`:
   - After `_handle_vanilla_worktree`, call `discover_repo_context(ctx, ctx.cwd)` to refresh `repo`

---

## Tests to Add/Update

- **`tests/commands/navigation/test_down.py`** — Add test: `erk down -d -f` when downstack branch shares the same worktree. Assert that `git checkout {parent}` + `gt delete {branch}` are in the output/script, and `git worktree remove` is NOT present.
- **`tests/commands/branch/test_delete.py`** (or similar) — Add test: deleting a branch whose worktree is the current worktree should not crash (use `_delete_branch` fake-driven test for the repo re-discovery).

---

## Verification

1. Reproduce the scenario locally: check out a plan branch into an existing worktree, then `erk down -d -f`
2. Verify the suggested command is `git checkout {parent} && gt delete -f --no-interactive {branch}` (not `erk br delete`)
3. Run `make fast-ci` to ensure existing tests pass
4. Manually test the crash fix by running `erk br delete` on a branch in the current worktree
