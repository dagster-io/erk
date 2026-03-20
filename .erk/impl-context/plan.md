# Plan: Replace `erk pr rebase` with `erk pr resolve-conflicts`

> **Replans:** #9210

## Context

`erk pr rebase` currently does two things: initiates rebases (via `gt restack` or `git rebase`) AND resolves conflicts. The user wants erk to stop initiating rebases locally — that's the user's job. Erk should only help resolve conflicts from an already in-progress rebase.

Remote CI infrastructure (`erk launch pr-rebase`, GitHub Action, exec script) stays unchanged — CI automation legitimately needs to initiate rebases autonomously.

## What Changed Since Original Plan

Nothing — the original plan (#9210) was never implemented. All files are in their original state. This replan corrects the missing `erk-plan` label and re-validates against current codebase.

## Investigation Findings

- `rebase_cmd.py` (156 lines) still exists with two-phase logic: mechanical rebase + conflict resolution via Claude
- Conflict resolution path is lines 134-155: detect conflicts, show files, confirm, launch TUI
- `stream_rebase` in `output.py` (lines 261-366) and `RebaseResult` (lines 252-258) are only used by `rebase_cmd.py` — safe to delete
- Gateway methods `is_rebase_in_progress()` and `get_conflicted_files()` exist in erk-shared and are ready to use
- Remote CI: `rebase_with_conflict_resolution.py`, `pr-rebase.yml`, constants — all untouched, all stay
- Test file `test_rebase.py` has 16 tests; 7 are conflict-resolution tests to adapt, rest are rebase-initiation tests to drop

## Implementation Steps

### 1. Create `src/erk/cli/commands/pr/resolve_conflicts_cmd.py`

New command extracted from `rebase_cmd.py` lines 134-155. No Graphite logic, no `--target` flag, no rebase initiation.

```python
@click.command("resolve-conflicts")
# --dangerous, --safe flags (same as current rebase_cmd)
def resolve_conflicts(ctx, *, dangerous, safe):
    # 1. resolve_dangerous (same pattern as rebase_cmd)
    # 2. Check executor.is_available()
    # 3. Check is_rebase_in_progress() -- error if False
    # 4. Show conflicted files
    # 5. Confirm with user
    # 6. execute_interactive(command="/erk:pr-resolve-conflicts", permission_mode="edits")
```

Error when no rebase in progress:
> "No rebase in progress. Start a rebase first with 'git rebase <branch>', 'gt restack', etc., then run this command when conflicts arise."

Pause when user declines:
> "Conflicts remain -- run 'erk pr resolve-conflicts' again when ready."

### 2. Create `.claude/commands/erk/pr-resolve-conflicts.md`

Copy from `.claude/commands/erk/pr-rebase.md` (62 lines) with updated framing:
- Description: "Resolve merge conflicts from an in-progress rebase"
- Remove "start a fresh rebase" language
- Add note: "This command resolves conflicts from a rebase already in progress. It does NOT initiate a rebase."
- Conflict resolution steps (check status, separate auto-generated files, resolve each, stage, `git rebase --continue`, loop, regenerate, verify, ask about pushing) remain identical

### 3. Create `tests/commands/pr/test_resolve_conflicts.py`

Adapt 8 tests from `test_rebase.py`:

| New Test | Source (test_rebase.py) |
|----------|------------------------|
| `test_rebase_in_progress_launches_tui` | line 95 |
| `test_no_rebase_in_progress_error` | NEW — verify error message |
| `test_user_declines` | line 258 |
| `test_claude_not_available` | line 233 |
| `test_safe_flag` | line 145 |
| `test_dangerous_and_safe_mutually_exclusive` | line 173 |
| `test_live_dangerously_false_runs_safe` | line 197 |
| `test_no_conflicted_files_still_confirms` | line 287 |

Use `build_workspace_test_context` (not graphite context — no graphite logic in new command).

### 4. Modify `src/erk/cli/commands/pr/__init__.py`

- Remove: `from erk.cli.commands.pr.rebase_cmd import rebase` (line 17) and `pr_group.add_command(rebase, name="rebase")` (line 38)
- Add: `from erk.cli.commands.pr.resolve_conflicts_cmd import resolve_conflicts` and `pr_group.add_command(resolve_conflicts, name="resolve-conflicts")`

### 5. Delete dead code from `src/erk/cli/output.py`

- Delete `RebaseResult` dataclass (lines 252-258)
- Delete `stream_rebase` function (lines 261-366)
- Keep: `DivergenceFixResult`, `stream_diverge_fix`, `format_implement_summary`, `stream_command_with_feedback`

### 6. Delete files

- `src/erk/cli/commands/pr/rebase_cmd.py`
- `.claude/commands/erk/pr-rebase.md`
- `tests/commands/pr/test_rebase.py`
- `tests/commands/pr/test_rebase_remote.py`

## Files NOT Changed

Remote CI infrastructure stays as-is:
- `src/erk/cli/commands/exec/scripts/rebase_with_conflict_resolution.py`
- `.github/workflows/pr-rebase.yml`
- `src/erk/cli/constants.py` (`REBASE_WORKFLOW_NAME`, `WORKFLOW_COMMAND_MAP`)
- `src/erk/cli/commands/launch_cmd.py`
- `src/erk/cli/commands/admin.py`
- `src/erk/capabilities/workflows/pr_rebase.py`
- All TUI references (`registry.py`, `workers.py`) — they dispatch `erk launch pr-rebase`

## Verification

1. `uv run pytest tests/commands/pr/test_resolve_conflicts.py` — new tests pass
2. `uv run pytest tests/commands/pr/` — no broken imports from removed files
3. `uv run pytest tests/commands/launch/` — launch pr-rebase tests still pass
4. `uv run pytest tests/tui/` — TUI tests still pass
5. `uv run ruff check src/erk/cli/output.py` — no lint issues after dead code removal
6. `uv run ty check src/erk/cli/commands/pr/resolve_conflicts_cmd.py` — type check passes
