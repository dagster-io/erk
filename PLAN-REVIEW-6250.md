# Plan: Migrate stack/move_cmd.py to Ensure (Step 1C.1)

Part of Objective #5185, Step 1C.1

## Goal

Migrate all `user_output() + raise SystemExit(1)` patterns in `src/erk/cli/commands/stack/move_cmd.py` to use the `Ensure` class, following the migration decision tree from `docs/learned/cli/output-styling.md`.

## Current State

The file already uses `Ensure` in 5 places (lines 27, 70-73, 80, 114-115). There are 8 remaining raw `user_output() + SystemExit(1)` patterns.

## Migration Plan

### Pattern 1: `_resolve_current_worktree` line 32-38 — `wt_path is None`
- **Method:** `Ensure.not_none()`
- **Change:** Replace the `if wt_path is None` block with `Ensure.not_none()` returning the path
- **Message:** Condense the multi-line message to a single Ensure-compatible message: `"Current directory ({cwd}) is not in any worktree - Use --worktree or --branch to specify the source"`

### Pattern 2: `resolve_source_worktree` line 60-61 — multiple flags
- **Method:** `Ensure.invariant()`
- **Change:** `Ensure.invariant(flag_count <= 1, "Only one of --current, --branch, or --worktree can be specified")`

### Pattern 3: `resolve_source_worktree` line 83-84 — fallthrough "invalid state"
- **Decision: DO NOT MIGRATE** — This is a fallthrough/catch-all error with no clear boolean condition. Per migration docs, these should not be migrated.

### Pattern 4: `execute_move` line 119-124 — uncommitted changes in source
- **Method:** `Ensure.invariant()`
- **Change:** `Ensure.invariant(not ctx.git.status.has_uncommitted_changes(source_wt) or force, "Uncommitted changes in source worktree '{source_wt.name}' - Commit, stash, or use --force to override")`

### Pattern 5: `execute_move` line 138-143 — uncommitted changes in target
- **Method:** `Ensure.invariant()`
- **Change:** `Ensure.invariant(not ctx.git.status.has_uncommitted_changes(target_wt) or force, "Uncommitted changes in target worktree '{target_wt.name}' - Commit, stash, or use --force to override")`

### Pattern 6: `execute_swap` line 181-182 — both worktrees need branches
- **Method:** `Ensure.invariant()`
- **Change:** `Ensure.invariant(source_branch is not None and target_branch is not None, "Both worktrees must have branches checked out for swap")`

### Pattern 7: `execute_swap` line 186-194 — uncommitted changes in swap
- **Method:** `Ensure.invariant()`
- **Change:** Combine the compound condition: `Ensure.invariant(not (has_uncommitted_source or has_uncommitted_target) or force, "Uncommitted changes detected in one or more worktrees - Commit, stash, or use --force to override")`

### Pattern 8: `move_stack` line 296-298 — source and target same
- **Method:** `Ensure.invariant()`
- **Change:** `Ensure.invariant(source_wt.resolve() != target_wt.resolve(), "Source and target worktrees are the same")`

## Files to Modify

- `src/erk/cli/commands/stack/move_cmd.py` — 7 patterns migrated, 1 kept as-is (fallthrough)

## Post-Migration Cleanup

- Remove `user_output` import if no longer used (check Pattern 3 fallthrough + the non-error `user_output` calls like line 133, 162, etc.)
- `user_output` will still be needed for non-error output (lines 133, 162, 198-200, 205, 216), so the import stays.

## Verification

1. Run `ruff` and `ty` to check for lint/type errors
2. Run existing tests for `move_cmd` (search for test file)
3. Verify: `grep -n "raise SystemExit(1)" src/erk/cli/commands/stack/move_cmd.py` shows only 1 remaining (the fallthrough on line 83-84)
4. Verify: no changes to non-error `user_output` calls (progress messages, success messages, swap confirmation)