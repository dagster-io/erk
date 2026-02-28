# Rename "Fix Conflicts Remote" to "Rebase Remote" and Always Rebase

## Context

The TUI's "Fix Conflicts Remote" action dispatches `pr-fix-conflicts` which rebases a PR branch onto its base branch and resolves conflicts with Claude. The name implies it only works when conflicts exist, but it actually performs a full rebase regardless. Additionally, the underlying script (`rebase_with_conflict_resolution.py`) has an early return when `behind == 0` that skips the rebase entirely.

The user wants:
1. Rename the action to "Rebase Remote" to reflect what it actually does
2. Remove the `behind == 0` early return so it always performs the full fetch/rebase/push cycle

## Changes

### 1. Remove `behind == 0` early return in exec script

**File:** `src/erk/cli/commands/exec/scripts/rebase_with_conflict_resolution.py`

- Remove the `if behind == 0: return RebaseSuccess(action="already-up-to-date", ...)` block (lines 221-226)
- Let the rebase always proceed — when behind == 0, `git rebase` is a no-op, then force push pushes unchanged content
- In the CLI handler (line 334), keep the `already-up-to-date` output for when `behind == 0` but after the rebase+push has completed. Change the `action` field logic: set to `"already-up-to-date"` when `behind == 0` AFTER the rebase completes (not before), so the caller can still show the appropriate message without generating a Claude summary
- Concretely: move the behind == 0 check to AFTER rebase+push, before summary generation. Return `RebaseSuccess(action="already-up-to-date", commits_behind=0, conflicts_resolved=())` after the push succeeds

### 2. Rename across TUI — `fix_conflicts_remote` → `rebase_remote`

This is a mechanical rename of the command ID, display names, method names, and string literals.

**`src/erk/tui/commands/registry.py`:**
- Rename `_display_fix_conflicts_remote` → `_display_rebase_remote`
- Rename `_display_copy_fix_conflicts_remote` → `_display_copy_rebase_remote`
- Change command ID `"fix_conflicts_remote"` → `"rebase_remote"`
- Change name `"Fix Conflicts Remote"` → `"Rebase Remote"`
- Change description `"fix-conflicts"` → `"rebase"`
- Change command ID `"copy_fix_conflicts_remote"` → `"copy_rebase_remote"`
- Update display name string `"erk launch pr-fix-conflicts"` → `"erk launch pr-fix-conflicts"` (keep CLI command name unchanged — only rename the TUI label)

**`src/erk/tui/screens/launch_screen.py`:**
- Rename key mapping `"fix_conflicts_remote": "f"` → `"rebase_remote": "f"`

**`src/erk/tui/app.py`:**
- Rename method `_fix_conflicts_remote_async` → `_rebase_remote_async`
- Update all string literals: `"fix-conflicts-pr-"` → `"rebase-pr-"`, `"Dispatching fix-conflicts"` → `"Dispatching rebase"`, `"Failed to dispatch fix-conflicts"` → `"Failed to dispatch rebase"`
- Update command ID checks: `"fix_conflicts_remote"` → `"rebase_remote"`, `"copy_fix_conflicts_remote"` → `"copy_rebase_remote"`

**`src/erk/tui/screens/plan_detail_screen.py`:**
- Rename binding `"fix_conflicts_remote"` → `"rebase_remote"`, label `"Fix Conflicts"` → `"Rebase"`
- Rename method `action_fix_conflicts_remote` → `action_rebase_remote`
- Update string literals in notify calls
- Update command ID checks in `execute_palette_command`

### 3. Update tests

**Test files to update (command ID / method name references):**
- `tests/tui/commands/test_registry.py`
- `tests/tui/app/test_plan_detail_screen.py`
- `tests/tui/commands/test_execute_command.py`
- `tests/tui/app/test_async_operations.py`
- `tests/tui/app/test_command_palette.py`
- `tests/tui/screens/test_launch_screen.py`
- `tests/commands/pr/test_fix_conflicts_remote.py` (if it tests the exec script behavior)

For test updates: search-and-replace `fix_conflicts_remote` → `rebase_remote`, `Fix Conflicts` → `Rebase`, `_fix_conflicts_remote_async` → `_rebase_remote_async` in each file. Verify string literal updates match the production code changes.

## What stays unchanged

- The CLI command name `erk launch pr-fix-conflicts` — no rename at CLI level
- The workflow file name `pr-fix-conflicts.yml` — no rename
- The workflow's `base_branch` input — still uses `pr.base_ref_name` (which is `master` for master-based PRs)

## Verification

1. Run `ruff check` and `ty check` for lint/type errors
2. Run `pytest tests/unit/cli/commands/exec/scripts/` for exec script behavior tests
3. Run `pytest tests/tui/` for TUI tests
4. Manual: `erk dash -i`, select a plan with a PR, press `l` then `f` — should show "Rebase Remote" and dispatch successfully
