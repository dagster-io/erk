# Plan: Show conflict state and confirm before launching Claude in `erk pr rebase`

## Context

When `erk pr rebase` hits conflicts (via `gt restack` or `git rebase`), it currently prints a brief message like "Restack hit conflicts. Launching Claude..." and immediately launches Claude TUI. The user wants two changes:

1. **Show conflicted files** before launching Claude, so the user understands the scope
2. **Confirm step** asking whether to launch Claude for interactive resolution

## Files to Modify

- `src/erk/cli/commands/pr/rebase_cmd.py` — main change
- `tests/commands/pr/test_rebase.py` — update tests

## Implementation

### 1. Add `_display_conflicts_and_confirm` helper in `rebase_cmd.py`

Extract a helper that:
- Calls `ctx.git.status.get_conflicted_files(cwd)` to get the list of conflicted files
- Displays the list with `click.echo`
- Calls `click.confirm("Launch Claude to resolve conflicts?", default=True)`
- Returns the boolean result

### 2. Call the helper before launching Claude TUI

Three code paths converge before the Claude TUI launch (line 121):
- Graphite restack hit conflicts (line 104)
- Git rebase hit conflicts (line 116)
- Rebase already in progress (line 118)

After all three paths print their status message, insert the conflict display + confirm step before the `executor.execute_interactive()` call. If the user declines, exit cleanly with a message like "Rebase paused. Run `erk pr rebase` again when ready."

The code at line 120-130 becomes:

```python
# Both paths converge: conflicts exist, show state and confirm
conflicted = ctx.git.status.get_conflicted_files(cwd)
if conflicted:
    click.echo(click.style("\nConflicted files:", fg="red", bold=True))
    for f in conflicted:
        click.echo(f"  {f}")
    click.echo()

if not click.confirm("Launch Claude to resolve conflicts?", default=True):
    click.echo("Rebase paused. Conflicts remain — run 'erk pr rebase' again when ready.")
    return

click.echo("Launching Claude...", err=True)
executor.execute_interactive(...)
```

### 3. Update tests

**Existing test `test_pr_rebase_non_graphite_conflict_launches_tui`:**
- Add `conflicted_files=["file.py"]` to FakeGit constructor
- Pass `input="y\n"` to `runner.invoke()` to simulate confirming
- Assert conflicted file name appears in output
- Assert confirm prompt appears in output

**Existing test `test_pr_rebase_in_progress_launches_tui`:**
- Add `conflicted_files=["src/context.py", "src/fast_llm.py"]` to FakeGit
- Pass `input="y\n"` to simulate confirming
- Assert files shown in output

**New test `test_pr_rebase_conflict_user_declines`:**
- Same setup as conflict test but pass `input="n\n"`
- Assert `executor.interactive_calls` is empty (Claude not launched)
- Assert "paused" message in output
- Assert exit_code == 0

**New test `test_pr_rebase_conflict_no_conflicted_files_still_confirms`:**
- Rebase fails but `get_conflicted_files` returns empty (edge case)
- Still shows confirm prompt, just no file list
- Pass `input="y\n"`, assert Claude is launched

## Verification

Run scoped tests:
```bash
uv run pytest tests/commands/pr/test_rebase.py -v
```
