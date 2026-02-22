# Move objective update from shell script into Python land-execute

## Context

After `erk land` merges a PR, the generated `.erk/bin/land.sh` script currently contains **two separate `erk exec` commands** plus a `cd`:

```bash
erk exec land-execute --flags "$@" || return 1
erk exec objective-update-after-land --objective 42 --pr "$PR_NUMBER" --branch "$BRANCH"
cd /target
```

This creates surface area for bugs: after `land-execute` finishes (which may pull latest master, delete worktrees, etc.), the second `erk exec` call runs in a different environment than expected. The user hit exactly this — `objective-update-after-land` failed with "No such command" because the `erk` binary resolved differently after the directory change.

The fix: move the objective update into `land-execute` so the shell script is minimal:

```bash
erk exec land-execute --flags --objective-number=42 "$@" || return 1
cd /target
```

## Changes

### 1. `src/erk/cli/commands/land_cmd.py` — `render_land_execution_script()`

Bake `--objective-number` into the `land-execute` command flags instead of emitting a separate shell command.

- Add `cmd_parts.append(f"--objective-number={objective_number}")` when `objective_number is not None`
- Remove the `objective_line` variable and all code that builds it
- Remove `{objective_line}` from the template string
- Keep the `objective_number` parameter (still needed to conditionally add the flag)

### 2. `src/erk/cli/commands/objective_helpers.py` — New helper function

Extract the objective update logic from `objective_update_after_land.py` into a reusable function:

```python
def run_objective_update_after_land(
    ctx: ErkContext,
    *,
    objective: int,
    pr: int,
    branch: str,
) -> None:
```

This function contains the `stream_command_with_feedback` call and success/failure output. It's fail-open (catches all errors, never raises).

### 3. `src/erk/cli/commands/exec/scripts/land_execute.py`

Stop ignoring `--objective-number`. After `_execute_land()` returns successfully, call the new helper:

```python
_execute_land(erk_ctx, ...)

# Objective update (fail-open — merge already succeeded)
if objective_number is not None:
    run_objective_update_after_land(
        erk_ctx, objective=objective_number, pr=pr_number, branch=branch
    )
```

Remove the comment about ignoring the value.

### 4. `src/erk/cli/commands/exec/scripts/objective_update_after_land.py`

Rewrite to call the shared helper from `objective_helpers.py`. This exec command stays available for manual retries but becomes a thin wrapper.

### 5. `tests/unit/cli/commands/land/test_render_land_script.py`

Update tests:
- `test_render_land_execution_script_bakes_in_static_flags`: Change assertion from checking for `erk exec objective-update-after-land --objective 42` to checking for `--objective-number=42` in the `land-execute` command line
- `test_render_land_execution_script_without_static_flags`: Keep assertion that `objective` is not in script
- `test_render_land_execution_script_objective_update_is_fail_open`: Remove (objective is no longer a separate line in the script)
- `test_render_land_execution_script_objective_uses_shell_variables`: Remove (objective no longer uses shell variables — it's a baked-in static flag)

### 6. Tests for objective update in land_execute

Add test(s) in `tests/unit/cli/commands/exec/scripts/test_land_execute.py` verifying that `--objective-number` triggers the objective update after merge.

## Files Modified

- `src/erk/cli/commands/land_cmd.py` (~line 1638-1675)
- `src/erk/cli/commands/objective_helpers.py` (add function)
- `src/erk/cli/commands/exec/scripts/land_execute.py` (~line 96-158)
- `src/erk/cli/commands/exec/scripts/objective_update_after_land.py` (simplify)
- `tests/unit/cli/commands/land/test_render_land_script.py`
- `tests/unit/cli/commands/exec/scripts/test_land_execute.py` (if exists, add test)

## Verification

1. Run existing land script rendering tests: `pytest tests/unit/cli/commands/land/test_render_land_script.py -x`
2. Run land execute tests: `pytest tests/unit/cli/commands/exec/scripts/test_land_execute.py -x`
3. Run objective update tests: `pytest tests/unit/cli/commands/exec/scripts/test_objective_update_after_land.py -x`
4. Run full land test suite: `pytest tests/unit/cli/commands/land/ tests/unit/cli/commands/exec/scripts/test_land_execute*.py -x`
