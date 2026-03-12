# Plan: Add `--dry-run` to `erk pr teleport`

## Context

`erk pr teleport` force-resets a local branch to match remote, discarding local commits and uncommitted changes. Users want a way to preview what would be lost before committing to the operation. The `--dry-run` flag will perform read-only operations (fetch, compute divergence, detect uncommitted changes) and report what would happen without making any mutations.

## Approach: Conditional-return pattern

Use the simpler conditional-return pattern (as in `reconcile_cmd.py`) rather than context recreation (as in `land_cmd.py`). Teleport's flow is linear — gather state, then mutate — so we gather state, display the report, and exit before mutations.

## Files to modify

- `src/erk/cli/commands/pr/teleport_cmd.py` — add flag, dry-run logic, report helper
- `tests/commands/pr/test_teleport.py` — add dry-run tests

## Implementation steps

### 1. Add `--dry-run` CLI flag

Add to the `@click.command` decorator stack, following existing pattern:
```python
@click.option("--dry-run", is_flag=True, help="Preview without making changes")
```
Add `dry_run: bool` parameter to `pr_teleport`. Pass through to both `_teleport_in_place` and `_teleport_new_slot`.

When `--dry-run` is active, force `script=False` (same as land command line 1584) so output is always human-readable.

### 2. Modify `_teleport_in_place` (add `dry_run` param)

After the fetch and ahead/behind computation (lines 200-205), insert dry-run logic:

1. **Gather state** (all read-only):
   - `ahead, behind` from `get_ahead_behind` (already computed for `_confirm_overwrite`)
   - `staged, modified, untracked` from `ctx.git.status.get_file_status(cwd)` (new call)
   - Whether branch exists locally (already computed)
   - Whether Graphite is managed, whether PR is stacked
   - Whether slot assignment exists
   - Whether `--sync` was requested

2. **If `dry_run`**: call `_display_dry_run_report(...)` and `raise SystemExit(0)`

3. **Skip**: force-reset, checkout, slot update, Graphite registration, navigation

The existing "already in sync" check (`ahead == 0 and behind == 0`) should still work — it fires before the dry-run report since being in sync means there's nothing to preview.

### 3. Modify `_teleport_new_slot` (add `dry_run` param)

The `_navigate_to_existing_worktree` check stays (it's read-only + navigation, same in dry-run).

After that, if `dry_run`:
1. Fetch the branch (read-only network call, needed to know if branch exists locally vs only on remote)
2. Compute state: is Graphite managed, is stacked, would create a new worktree slot
3. Call `_display_dry_run_report(...)` with `is_new_slot=True`
4. `raise SystemExit(0)`

Skip: `_fetch_and_update_branch` mutation part, Graphite registration, worktree creation.

### 4. Create `_display_dry_run_report` helper

```python
def _display_dry_run_report(
    ctx: ErkContext,
    *,
    pr_number: int,
    branch_name: str,
    base_ref_name: str,
    ahead: int,
    behind: int,
    staged: list[str],
    modified: list[str],
    untracked: list[str],
    is_new_slot: bool,
    branch_exists_locally: bool,
    is_graphite_managed: bool,
    trunk: str,
    sync: bool,
) -> None:
```

**Output format:**

```
Dry run: erk pr teleport 123

  Local state that would be discarded:
    3 local commit(s) ahead of remote (would be lost)
    2 staged file(s): src/foo.py, src/bar.py
    1 modified file(s): src/baz.py
    5 untracked file(s)

  Operations:
    Would fetch origin/feature-branch
    Would force-reset 'feature-branch' to match remote
    Would checkout 'feature-branch'
    Would update slot assignment
    Would track branch with Graphite (base: main)
    Would run gt submit --no-interactive

[DRY RUN] No changes made
```

If no local state would be discarded (all counts zero, no uncommitted changes), omit the "Local state" section entirely.

For `--new-slot`, operations include "Would create new worktree slot" instead of slot/checkout lines.

Use `click.echo` + `click.style` for formatting (consistent with existing teleport output).

### 5. Tests

Add to `tests/commands/pr/test_teleport.py`:

1. **`test_teleport_dry_run_in_place_shows_local_state`** — Set up branch with `ahead_behind=(2, 1)` and `file_statuses` with staged/modified files. Verify output includes commit counts, file info, "Would force-reset", and "[DRY RUN]" footer. Verify no mutations via `git.created_branches_force` being empty.

2. **`test_teleport_dry_run_in_place_already_in_sync`** — `ahead_behind=(0, 0)`. Verify "already in sync" message (same as non-dry-run behavior).

3. **`test_teleport_dry_run_no_mutations`** — Verify `git.checked_out_branches` is empty, `git.created_branches_force` is empty (or equivalent mutation tracker).

4. **`test_teleport_dry_run_new_slot`** — Verify "Would create new worktree slot" in output.

5. **`test_teleport_dry_run_with_sync`** — Verify "Would run gt submit" appears when `--sync` is passed.

6. **`test_teleport_dry_run_with_graphite`** — Verify Graphite operations appear. Verify no actual Graphite tracking happened.

## Verification

1. Run `uv run pytest tests/commands/pr/test_teleport.py` — all existing + new tests pass
2. Run `uv run ty check src/erk/cli/commands/pr/teleport_cmd.py` — type checks pass
3. Run `uv run ruff check src/erk/cli/commands/pr/teleport_cmd.py` — lint passes
4. Manual: `erk pr teleport <number> --dry-run` on a real PR to verify output formatting
