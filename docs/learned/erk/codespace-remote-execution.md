---
title: Codespace Remote Execution Pattern
read_when:
  - "implementing remote command execution on codespaces"
  - "working with nohup or background processes on codespaces"
  - "debugging codespace remote execution failures"
  - "adding new erk commands that run remotely"
---

# Codespace Remote Execution Pattern

Erk uses a **fire-and-forget** pattern for executing commands remotely on GitHub Codespaces. Commands are wrapped with environment bootstrap logic and run in the background via `nohup`.

## The Pattern

All remoteable commands use `build_codespace_run_command()` from `src/erk/core/codespace_run.py`:

```python
from erk.core.codespace_run import build_codespace_run_command

# Wrap the erk CLI command
remote_cmd = build_codespace_run_command("erk objective next-plan 42")

# Execute via codespace gateway
codespace_gateway.run_ssh_command(
    codespace_name="mycodespace",
    command=remote_cmd
)
```

## What It Does

The wrapper produces a bash command that:

1. **Bootstraps the environment**: `git pull && uv sync && source .venv/bin/activate`
2. **Runs the command in background**: `nohup {erk_command} > /tmp/erk-run.log 2>&1 &`
3. **Returns immediately**: The SSH connection closes while the command continues running

### Example Output

Input:

```python
build_codespace_run_command("erk objective next-plan 42")
```

Output:

```bash
bash -l -c 'git pull && uv sync && source .venv/bin/activate && nohup erk objective next-plan 42 > /tmp/erk-run.log 2>&1 &'
```

## Fire-and-Forget Semantics

**Key property**: The command returns immediately, even if the erk process is still running.

This means:

- ✅ The SSH connection closes quickly
- ✅ You can queue multiple commands
- ❌ You don't get output or exit codes
- ❌ You can't check if the command succeeded

## Output Logging

All output (stdout and stderr) goes to `/tmp/erk-run.log` on the codespace:

```bash
# Check the log manually
gh codespace ssh -c mycodespace -- tail -f /tmp/erk-run.log
```

## Debugging

If a remote command fails:

1. **Check the log file**: `gh codespace ssh -c mycodespace -- cat /tmp/erk-run.log`
2. **Verify environment**: Ensure `git pull` and `uv sync` succeeded
3. **Test locally**: Run the same erk command on your local machine first
4. **Check process**: See if the process is still running with `gh codespace ssh -c mycodespace -- ps aux | grep erk`

## When to Use This Pattern

✅ **Use for**:

- Long-running commands (plan implementation, objective processing)
- Commands that don't need immediate feedback
- Async workflows where you check results later

❌ **Don't use for**:

- Commands that need output immediately
- Commands with interactive prompts
- Short commands where you want the exit code

For interactive or short commands, use `codespace_gateway.exec_ssh_interactive()` instead.

## Related Documentation

- [Codespace Gateway](../gateway/codespace-gateway.md) - Gateway ABC for codespace operations
- [Composable Remote Commands](../architecture/composable-remote-commands.md) - Template for adding new remote commands
- [Codespace Patterns](../cli/codespace-patterns.md) - `resolve_codespace()` helper usage
