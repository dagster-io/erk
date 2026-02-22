# Plan: Change `erk land` default to direct execution

## Context

Currently `erk land` always generates a deferred shell script that the user must `source` to execute. This exists because Python can't `cd` the parent shell, and the default behavior navigates to trunk after landing. This adds friction for the common case where the user just wants to merge+cleanup without navigation.

**Goal**: Make the default `erk land` execute directly (merge + cleanup, no navigation, no source command). Move the current default behavior (navigate to trunk) behind a new `--down` flag that mirrors `--up`.

### Behavior Matrix

| Invocation | Merge | Cleanup | Navigation | Source command |
|---|---|---|---|---|
| `erk land` (new default) | Yes | Yes | No | No |
| `erk land --down` (new flag) | Yes | Yes | To trunk | Yes |
| `erk land --up` (unchanged) | Yes | Yes | To child | Yes |

## Files to Modify

### 1. `src/erk/cli/commands/land_cmd.py` (main changes)

**Add `--down` flag** (next to `--up` at line ~1743):
```python
@click.option(
    "--down",
    "down_flag",
    is_flag=True,
    help="Navigate to trunk after landing (produces source command)",
)
```

**Add `down_flag: bool` parameter** to `land()` function signature (line ~1772).

**Add mutual exclusivity check** at start of `land()` body (after line ~1810):
```python
Ensure.invariant(
    not (up_flag and down_flag),
    "--up and --down are mutually exclusive.\n"
    "--up navigates to child branch, --down navigates to trunk.",
)
```

**Branch between direct execution and deferred script** (replace lines ~1855-1865):
- When `up_flag or down_flag`: call `_land_target()` (current behavior, generates source command)
- When neither: call new `_execute_land_directly()` (runs both pipelines inline)

**Create `_execute_land_directly()` function**:
- Accepts `ctx`, `repo`, `target` (LandTarget), `script`, `pull_flag`, `no_delete`, `cleanup_confirmed`
- Handle dry-run mode (show what would happen, exit)
- Build `LandState` with `target_child_branch=None`, `up_flag=False`
- Call `run_execution_pipeline()` directly
- Run objective update (fail-open) via `run_objective_update_after_land`
- If `script=True`: output no-op script path for shell wrapper compatibility
- Exit successfully

Key: The existing execution pipeline with `skip_activation_output=True` already handles the no-navigation case correctly - cleanup happens, optional pull, then `SystemExit(0)`.

**Update display flags in `_land_target()`** (line ~1363): When called via `--down` (not `--up`), don't add `--up` to display flags.

**Update `land()` docstring** (line ~1783) to document new behavior.

### 2. `src/erk/cli/commands/land_pipeline.py` (no structural changes)

No changes needed. The existing `LandState` with `up_flag=False` and `target_child_branch=None` already represents "no navigation" correctly. The execution pipeline handles this path.

### 3. `src/erk/cli/commands/exec/scripts/land_execute.py` (minor)

**Add `--down` flag** for `"$@"` passthrough compatibility (accepted but ignored, since navigate-to-trunk is already the default when `--up` is not passed). Add to Click options and function signature.

### 4. `tests/commands/land/test_core.py` (update existing tests)

`test_land_outputs_deferred_execution_script`: Currently runs `["land", "--script", "--force"]` and expects a deferred script. With the new default, this would trigger direct execution. **Add `--down`** to preserve the test: `["land", "--script", "--force", "--down"]`.

### 5. New tests for direct execution (in `tests/commands/land/`)

Add tests to an appropriate file (likely `test_core.py` or a new `test_direct_execution.py`):
- `test_land_default_executes_directly`: No `--up`/`--down`, verify PR is merged and branch is cleaned up inline (no deferred script)
- `test_land_up_and_down_mutually_exclusive`: Both flags, verify error

### 6. `.claude/commands/erk/land.md` (no changes needed)

The skill uses `erk land <PR_NUMBER> --force` which still works (direct execution is the new default).

## Verification

1. Run existing land tests: `pytest tests/commands/land/ tests/unit/cli/commands/land/`
2. Run land-execute tests: `pytest tests/unit/cli/commands/exec/scripts/test_land_execute.py`
3. Run ty type checker on modified files
4. Run ruff linter
