# Fix: Stream codespace run output to terminal

## Problem

`erk codespace run objective next-plan` uses `run_ssh_command` which calls `gh codespace ssh` **without the `-t` flag** (no TTY allocation). The remote `erk objective next-plan` command launches Claude via `os.execvp("claude", ...)`, which needs a TTY to stream output. Without it, the command appears to hang with no visible progress after the bootstrap (git pull, uv sync) completes.

## Fix

**Switch from `run_ssh_command` to `exec_ssh_interactive`** in the codespace run wrapper.

`exec_ssh_interactive` already:
- Allocates a pseudo-TTY (`-t` flag)
- Replaces the current process via `os.execvp` (so output streams directly)

This is the correct call for this use case since `erk objective next-plan` launches an interactive Claude session on the remote side.

### File: `src/erk/cli/commands/codespace/run/objective/next_plan_cmd.py`

Replace the `run_ssh_command` + exit code handling with `exec_ssh_interactive`:

```python
# Before:
exit_code = ctx.codespace.run_ssh_command(codespace.gh_name, remote_cmd)
if exit_code == 0:
    click.echo("Command completed successfully.", err=True)
else:
    click.echo(f"Error: SSH command exited with code {exit_code}.", err=True)
    raise SystemExit(exit_code)

# After:
ctx.codespace.exec_ssh_interactive(codespace.gh_name, remote_cmd)
```

Since `exec_ssh_interactive` replaces the process (`NoReturn`), the exit code handling and success/error messages are no longer needed — the SSH process's exit code becomes the erk process's exit code automatically.

### File: `tests/unit/cli/commands/codespace/run/objective/test_next_plan_cmd.py`

Update tests to assert `exec_ssh_interactive` is called instead of `run_ssh_command`.

## Verification

1. Run existing tests via devrun to see what needs updating
2. Update tests to match new gateway method call
3. Run tests again to confirm they pass