# Move objective update into land-execute

## Context

After landing PR #7544, `erk exec objective-update-after-land` failed with "No such command" because the worktree's erk installation didn't have that exec script registered. The root cause: `render_land_execution_script()` emits TWO separate `erk exec` commands in the generated `land.sh`:

```bash
erk exec land-execute ... || return 1
erk exec objective-update-after-land --objective 7390 ...   # <-- fails if erk version mismatch
cd /path/to/target
```

If the erk binary that generated the script differs from the one running it, the second command may not exist. The fix: make the generated script call only ONE command, with `land-execute` handling everything internally.

## Changes

### 1. `land-execute` handles objective update internally

**File:** `src/erk/cli/commands/exec/scripts/land_execute.py`

- After `_execute_land()` succeeds and `objective_number` is provided, call the objective update logic directly
- Extract the core logic from `objective_update_after_land.py` into a helper function both can share
- Keep fail-open behavior: if objective update fails, print warning but exit 0

### 2. Extract shared objective update function

**File:** `src/erk/cli/commands/exec/scripts/objective_update_after_land.py`

- Extract the body into a function like `run_objective_update(ctx, *, objective, pr, branch)`
- The click command calls this function
- `land_execute` also calls this function after successful land

### 3. Remove separate command from generated script

**File:** `src/erk/cli/commands/land_cmd.py` — `render_land_execution_script()`

- Remove the `objective_line` logic (lines 1642-1650) that emits `erk exec objective-update-after-land`
- Instead, pass `--objective-number=N` to the `land-execute` command line (it already accepts this flag)
- The generated script becomes a single command again

### 4. Update land-execute comment

**File:** `src/erk/cli/commands/exec/scripts/land_execute.py`

- Remove the comment at lines 142-145 that says objective update is handled by a separate command
- Document that objective update is now inline

## Files to modify

1. `src/erk/cli/commands/exec/scripts/objective_update_after_land.py` — extract helper
2. `src/erk/cli/commands/exec/scripts/land_execute.py` — call helper after successful land
3. `src/erk/cli/commands/land_cmd.py` — simplify `render_land_execution_script()`

## Verification

1. Run unit tests for land and objective exec scripts
2. Test `erk land --script` output to verify it no longer emits a separate `objective-update-after-land` line
3. Verify the generated script has `--objective-number=N` on the `land-execute` command line