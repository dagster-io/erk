---
title: Codespace Remote Execution Pattern
read_when:
  - "implementing remote command execution on codespaces"
  - "working with streaming command output on codespaces"
  - "debugging codespace remote execution failures"
  - "adding new erk commands that run remotely"
---

# Codespace Remote Execution Pattern

Erk uses a **streaming execution** pattern for running commands remotely on GitHub Codespaces. Commands are wrapped with environment bootstrap logic and run in the foreground, streaming output back to the caller in real-time.

## The Pattern

All remoteable commands use `build_codespace_ssh_command()` from `src/erk/core/codespace_run.py`:

```python
from erk.core.codespace_run import build_codespace_ssh_command

# Wrap the erk CLI command
remote_cmd = build_codespace_ssh_command("erk objective next-plan 42")

# Execute via codespace gateway
exit_code = codespace_gateway.run_ssh_command(
    codespace_name="mycodespace",
    command=remote_cmd
)
```

## What It Does

The wrapper produces a bash command that:

1. **Bootstraps the environment**: `git pull && uv sync && source .venv/bin/activate`
2. **Runs the command in foreground**: `{erk_command}` (no backgrounding)
3. **Streams output**: stdout/stderr appear in real-time on the caller's terminal
4. **Returns exit code**: The SSH connection stays open until the command completes

### Example Output

Input:

```python
build_codespace_ssh_command("erk objective next-plan 42")
```

Output:

```bash
bash -l -c 'git pull && uv sync && source .venv/bin/activate && erk objective next-plan 42'
```

## Streaming Semantics

**Key property**: The command runs synchronously, blocking until completion.

This means:

- ✅ You get real-time output in your terminal
- ✅ You get the actual exit code
- ✅ You can verify success immediately
- ❌ You must wait for the command to complete
- ❌ The SSH connection stays open during execution

## Output Handling

All output (stdout and stderr) streams directly to your terminal in real-time. No log files are created on the remote side.

## Debugging

If a remote command fails:

1. **Check the output**: Errors appear directly in your terminal
2. **Verify exit code**: The command's exit code is returned to the caller
3. **Verify environment**: Look for `git pull` and `uv sync` errors in the output
4. **Test locally**: Run the same erk command on your local machine first

## When to Use This Pattern

✅ **Use for**:

- Commands where you need to see output in real-time
- Commands where exit code verification is important
- Any command where synchronous execution is acceptable

❌ **Don't use for**:

- Commands with interactive prompts (use `exec_ssh_interactive()` instead)
- Commands where you need true fire-and-forget behavior

## Related Documentation

- [Codespace Gateway](../gateway/codespace-gateway.md) - Gateway ABC for codespace operations
- [Composable Remote Commands](../architecture/composable-remote-commands.md) - Template for adding new remote commands
- [Codespace Patterns](../cli/codespace-patterns.md) - `resolve_codespace()` helper usage
