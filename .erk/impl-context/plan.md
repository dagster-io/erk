# Plan: Replace `erk pr rebase` with `erk pr resolve-conflicts`

## Context

`erk pr rebase` currently does two things: initiates rebases (via `gt restack` or `git rebase`) AND resolves conflicts. The user wants erk to stop initiating rebases -- that's the user's job. Erk should only help resolve conflicts from an already in-progress rebase.

The remote CI workflow (`erk launch pr-rebase`, the GitHub Action, the exec script) stays unchanged -- CI automation legitimately needs to initiate rebases autonomously.

## Files to Create

### 1. `src/erk/cli/commands/pr/resolve_conflicts_cmd.py`

New command that only handles in-progress rebases with conflicts. Extracted from the convergence path in `rebase_cmd.py` (lines 134-155). No Graphite logic, no `--target` flag, no rebase initiation.

```python
@click.command("resolve-conflicts")
# --dangerous, --safe flags (same as current)
def resolve_conflicts(ctx, *, dangerous, safe):
    # 1. resolve_dangerous
    # 2. Check executor.is_available()
    # 3. Check is_rebase_in_progress() -- error if False
    # 4. Show conflicted files
    # 5. Confirm with user
    # 6. execute_interactive(command="/erk:pr-resolve-conflicts", permission_mode="edits")
```

Error message when no rebase in progress:
> "No rebase in progress. Start a rebase first with 'git rebase <branch>', 'gt restack', etc., then run this command when conflicts arise."

Pause message when user declines:
> "Conflicts remain -- run 'erk pr resolve-conflicts' again when ready."

### 2. `.claude/commands/erk/pr-resolve-conflicts.md`

Same conflict resolution steps as current `pr-rebase.md` (steps 1-8), with updated framing:
- Description: "Resolve merge conflicts from an in-progress rebase"
- Remove the "start a fresh rebase" language
- Add note: "This command resolves conflicts from a rebase already in progress. It does NOT initiate a rebase."
- Steps remain identical (check status, separate auto-generated files, resolve each, stage, `git rebase --continue`, loop, regenerate, verify, ask about pushing)

### 3. `tests/commands/pr/test_resolve_conflicts.py`

Tests adapted from existing `test_rebase.py`, keeping only the conflict-resolution tests:

| Test | Source |
|------|--------|
| rebase_in_progress_launches_tui | `test_pr_rebase_in_progress_launches_tui` (line 95) |
| no_rebase_in_progress_error | New -- verify error message |
| user_declines | `test_pr_rebase_conflict_user_declines` (line 258) |
| claude_not_available | `test_pr_rebase_claude_not_available` (line 233) |
| safe_flag | `test_pr_rebase_safe_flag_disables_dangerous` (line 145) |
| dangerous_and_safe_mutually_exclusive | `test_pr_rebase_dangerous_and_safe_mutually_exclusive` (line 173) |
| live_dangerously_false | `test_pr_rebase_live_dangerously_false_runs_safe` (line 197) |
| no_conflicted_files_still_confirms | `test_pr_rebase_conflict_no_conflicted_files_still_confirms` (line 287) |

All tests invoke `["resolve-conflicts", ...]` and assert command is `/erk:pr-resolve-conflicts`. Uses `build_workspace_test_context` (not graphite context -- no graphite-specific logic in new command).

## Files to Modify

### 4. `src/erk/cli/commands/pr/__init__.py`

- Remove: `from erk.cli.commands.pr.rebase_cmd import rebase` and `pr_group.add_command(rebase, name="rebase")`
- Add: `from erk.cli.commands.pr.resolve_conflicts_cmd import resolve_conflicts` and `pr_group.add_command(resolve_conflicts, name="resolve-conflicts")`

### 5. `src/erk/cli/output.py`

Delete dead code (unused after removing `rebase_cmd.py`):
- `RebaseResult` dataclass (lines 252-258)
- `stream_rebase` function (lines 261-366)

Keep: `DivergenceFixResult`, `stream_diverge_fix`, `format_implement_summary`, `stream_command_with_feedback`

## Files to Delete

### 6. `src/erk/cli/commands/pr/rebase_cmd.py`
### 7. `.claude/commands/erk/pr-rebase.md`
### 8. `tests/commands/pr/test_rebase.py`
### 9. `tests/commands/pr/test_rebase_remote.py` (already just a comment file)

## Files NOT Changed

Remote CI infrastructure stays as-is (pr-rebase is accurate naming for the remote workflow):
- `src/erk/cli/commands/exec/scripts/rebase_with_conflict_resolution.py`
- `.github/workflows/pr-rebase.yml`
- `src/erk/cli/constants.py` (`REBASE_WORKFLOW_NAME`, `WORKFLOW_COMMAND_MAP`)
- `src/erk/cli/commands/launch_cmd.py` (`_dispatch_pr_rebase`, all launch logic)
- `src/erk/cli/commands/admin.py` (`CLAUDE_CI_WORKFLOWS`)
- `src/erk/capabilities/workflows/pr_rebase.py`
- All TUI references (`registry.py`, `workers.py`) -- they dispatch `erk launch pr-rebase`
- All tests for the above unchanged files

## Verification

1. Run `uv run pytest tests/commands/pr/test_resolve_conflicts.py` -- new tests pass
2. Run `uv run pytest tests/commands/pr/` -- no broken imports from removed files
3. Run `uv run pytest tests/commands/launch/` -- launch pr-rebase tests still pass
4. Run `uv run pytest tests/tui/` -- TUI tests still pass
5. Run `uv run ruff check src/erk/cli/output.py` -- no lint issues after dead code removal
6. Run `uv run ty check src/erk/cli/commands/pr/resolve_conflicts_cmd.py` -- type check passes
