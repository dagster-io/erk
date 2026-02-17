# Fix: land.sh should not cd on merge failure

## Context

When `erk land` fails to merge a PR (e.g., merge conflicts), the generated `land.sh` script still executes the `cd` to trunk, moving the user out of their worktree. The branch deletion is correctly prevented by the Python execution pipeline (it stops at the first `LandError`), but the shell script lacks error checking on the `erk exec land-execute` call.

## Change

**File:** `src/erk/cli/commands/land_cmd.py` (line ~1675 in `render_land_execution_script`)

Add `|| return 1` after the `erk exec land-execute` command in the generated shell script template. Since the script is `source`d, `return` stops execution without closing the user's shell.

Current:
```python
return f"""...
{erk_cmd}
cd {target_path_str}
"""
```

Changed:
```python
return f"""...
{erk_cmd} || return 1
cd {target_path_str}
"""
```

This ensures that when the merge fails (exit code 1), the script stops immediately - no `cd`, no moving the user out of their worktree.

## Verification

1. Run existing land tests to ensure no regressions
2. Verify the generated script content includes `|| return 1` by checking test assertions on `render_land_execution_script` output