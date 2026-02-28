# Plan: Make `--script` mode resilient to errors in `erk br co`

## Context

The shell integration pattern `source "$(erk br co --script)"` breaks when the command fails. On success, stdout contains a path to an activation script. On failure, all error messages correctly go to stderr, but **stdout is empty**. Then `source ""` runs, producing the confusing error `source: no such file or directory:`.

**User's specific case**: `erk br co --new-slot --for-plan 8424 --script` failed because the branch was already checked out in another slot. The error message appeared correctly on stderr, but the empty stdout caused `source` to break.

**Goal**: When `--script` mode fails, output a path to a minimal error script (`return 1`) on stdout. This way `source` gets a valid script, the script returns non-zero, and `&&` chains stop cleanly.

## Approach

Extract the `branch_checkout()` body into `_branch_checkout_impl()` and wrap the call with a `script_error_handler` context manager that catches errors in `--script` mode. This protects against all 14 error paths in the function without modifying any of them individually.

## Changes

### 1. Add `render_error_script()` to `src/erk/cli/activation.py`

A minimal function returning `"# erk error\nreturn 1\n"`. Placed here because `activation.py` owns all script rendering functions.

### 2. Add `script_error_handler` context manager to `src/erk/cli/commands/checkout_helpers.py`

Context manager + `_write_error_script_and_exit()` helper. Handles three exception types:

- **`click.ClickException`**: Print error to stderr ourselves (Click's handler won't run since we catch first), write error script, exit 1
- **`SystemExit(0)`**: Re-raise (success exit from `_setup_impl_for_plan`)
- **`SystemExit(non-zero)`**: Error already printed via `user_output()`, just write error script, exit 1
- **`RuntimeError`**: Print error to stderr, write error script, exit 1

Uses `ctx.script_writer.write_activation_script()` to write the error script, then `result.output_for_shell_integration()` to output its path to stdout.

### 3. Modify `src/erk/cli/commands/branch/checkout_cmd.py`

Extract the entire `branch_checkout()` body (lines 382-669) into `_branch_checkout_impl()` with the same parameters. The `branch_checkout()` Click handler becomes a thin wrapper:

```python
def branch_checkout(ctx, branch, for_plan, no_slot, new_slot, force, script):
    handler = script_error_handler(ctx) if script else contextlib.nullcontext()
    with handler:
        _branch_checkout_impl(ctx, branch, for_plan, no_slot, new_slot, force, script)
```

This avoids re-indenting the ~290-line body. The body moves to `_branch_checkout_impl` unchanged.

### 4. Add tests to `tests/commands/branch/test_checkout_cmd.py`

- **`test_checkout_script_mode_error_writes_error_script`**: `--new-slot --script` with branch already checked out produces error script on stdout (not empty)
- **`test_checkout_script_mode_success_unaffected`**: Existing success path still works (regression test)

## Key files

| File | Change |
|------|--------|
| `src/erk/cli/activation.py` | Add `render_error_script()` |
| `src/erk/cli/commands/checkout_helpers.py` | Add `script_error_handler`, `_write_error_script_and_exit` |
| `src/erk/cli/commands/branch/checkout_cmd.py` | Extract body to `_branch_checkout_impl`, add wrapper |
| `tests/commands/branch/test_checkout_cmd.py` | Add script-mode error tests |

## Reusable existing code

- `ctx.script_writer.write_activation_script()` — writes script to temp file, returns `ScriptResult`
- `ScriptResult.output_for_shell_integration()` — outputs path to stdout via `machine_output()`
- `user_output()` — routes to stderr (`erk_shared/output/output.py`)

## Verification

1. Run `pytest tests/commands/branch/test_checkout_cmd.py` — all existing + new tests pass
2. Run `make fast-ci` to verify no regressions
3. Manual test: `source "$(erk br co --new-slot --for-plan 8424 --script)" && echo "should not print"` — error appears on stderr, no `source: no such file` error, "should not print" does not appear
