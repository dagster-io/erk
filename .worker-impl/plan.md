# Plan: Stream codespace command output instead of fire-and-forget

## Summary

Remove the fire-and-forget (`nohup ... &`) pattern from `build_codespace_run_command` so that the erk command runs in the foreground through SSH, streaming its output back to the caller in real-time.

## Changes

### 1. `src/erk/core/codespace_run.py`

Rename `build_codespace_run_command` → `build_codespace_ssh_command` (reflects that it's no longer fire-and-forget). Remove `nohup`, log redirect, and backgrounding:

```python
def build_codespace_ssh_command(erk_command: str) -> str:
    return (
        f"bash -l -c 'git pull && uv sync && source .venv/bin/activate"
        f" && {erk_command}'"
    )
```

### 2. `src/erk/cli/commands/codespace/run/objective/next_plan_cmd.py`

- Update import to `build_codespace_ssh_command`
- Change success message from "Command dispatched successfully." → "Command completed successfully." (it now runs synchronously, so the exit code reflects the actual command result)

### 3. `tests/unit/core/codespace/test_codespace_run.py`

- Rename references to `build_codespace_ssh_command`
- Replace `test_build_codespace_run_command_includes_nohup` with a test that verifies the command runs in the foreground (no `nohup`, no `&`, no `/tmp/erk-run.log`)
- Update `test_build_codespace_run_command_preserves_erk_command` to check the command directly (not prefixed with `nohup`)

### 4. `tests/unit/cli/commands/codespace/run/objective/test_next_plan_cmd.py`

- Update success message assertion: "Command completed successfully" instead of "Command dispatched successfully"

### 5. Documentation updates

- `docs/learned/erk/codespace-remote-execution.md` — Rewrite to describe the streaming/synchronous pattern instead of fire-and-forget
- `docs/learned/architecture/composable-remote-commands.md` — Update template and description to reflect synchronous execution

## Files modified

| File | Change |
|---|---|
| `src/erk/core/codespace_run.py` | Remove nohup/backgrounding, rename function |
| `src/erk/cli/commands/codespace/run/objective/next_plan_cmd.py` | Update import and success message |
| `tests/unit/core/codespace/test_codespace_run.py` | Update all 4 tests for new behavior and name |
| `tests/unit/cli/commands/codespace/run/objective/test_next_plan_cmd.py` | Update success message assertion |
| `docs/learned/erk/codespace-remote-execution.md` | Rewrite for streaming pattern |
| `docs/learned/architecture/composable-remote-commands.md` | Update template and descriptions |

## Verification

1. Run unit tests: `pytest tests/unit/core/codespace/test_codespace_run.py`
2. Run command tests: `pytest tests/unit/cli/commands/codespace/run/objective/test_next_plan_cmd.py`
3. Run ty/ruff for type and lint checks