---
title: Codespace Remote Execution Pattern
read_when:
  - "adding new remote execution commands via codespaces"
  - "implementing fire-and-forget command patterns"
  - "building commands that dispatch work to background processes"
  - "extending erk codespace run with new subcommands"
---

# Codespace Remote Execution Pattern

Remote execution enables fire-and-forget dispatch of long-running erk operations to GitHub Codespaces. The command returns immediately while execution continues asynchronously on the remote codespace.

## Overview

**Fire-and-forget semantics:**

- Command invocation returns immediately after dispatch
- Execution continues on codespace in background
- No streaming output to user terminal
- User retains control of local CLI immediately

**Use cases:**

- Long-running objective workflows (10+ minutes)
- Parallel processing of multiple tasks
- Batch operations requiring significant compute
- Any workflow that would block local terminal

**Tradeoffs:**

- ✅ Async execution: user doesn't wait for completion
- ✅ Resource isolation: runs on codespace, not local machine
- ❌ No live output: cannot see progress in real-time
- ❌ Debugging: must SSH to codespace to check logs

## Architecture

### Command Builder Function

`build_codespace_run_command()` is the single source of truth for remote execution setup:

```python
from erk.core.codespace_run import build_codespace_run_command

remote_cmd = build_codespace_run_command("erk objective next-plan 42")
```

**What it does:**

1. Wraps the erk CLI command in a shell wrapper: `bash -l -c '...'`
2. Sets up environment before execution:
   - `git pull` to sync latest code
   - `uv sync` to install dependencies
   - `. .venv/bin/activate` to activate virtual environment
3. Redirects output to `/tmp/erk-run.log` for later inspection
4. Uses `nohup` for background execution that survives SSH disconnect

**Shell wrapper template:**

```bash
bash -l -c 'cd /workspaces/erk && \
  git pull && \
  uv sync && \
  . .venv/bin/activate && \
  nohup erk objective next-plan 42 > /tmp/erk-run.log 2>&1 &'
```

### Output Logging

All output (stdout and stderr) is written to `/tmp/erk-run.log` on the codespace.

**To check execution results:**

```bash
# SSH to codespace
erk codespace connect

# View logs
cat /tmp/erk-run.log
# or
tail -f /tmp/erk-run.log  # Follow live progress
```

## Implementation Pattern

### Anatomy of a Remote Command

Every remote command follows this structure:

```python
@click.command()
@click.argument("issue_ref")
@click.option("--codespace", "-c", help="Codespace name (defaults to configured default)")
@click.pass_context
def next_plan_cmd(ctx: click.Context, issue_ref: str, codespace: str | None) -> None:
    """Execute 'erk objective next-plan' on a remote codespace."""
    # 1. Get context
    cmd_ctx = get_command_context(ctx)

    # 2. Resolve codespace (by name or default)
    cs = resolve_codespace(cmd_ctx.codespace_registry, codespace)

    # 3. Start codespace if stopped
    cmd_ctx.codespace.start_codespace(cs.gh_name)

    # 4. Build remote command
    remote_cmd = build_codespace_run_command(f"erk objective next-plan {issue_ref}")

    # 5. Execute via SSH
    exit_code = cmd_ctx.codespace.run_ssh_command(cs.gh_name, remote_cmd)

    # 6. Report to user
    if exit_code == 0:
        echo("✓ Remote execution dispatched")
    else:
        echo(f"✗ Failed to dispatch (exit {exit_code})")
        sys.exit(exit_code)
```

### Key Components

**1. Codespace Resolution**

Use `resolve_codespace()` to handle name/default lookup with consistent error messages:

```python
from erk.cli.commands.codespace.helpers import resolve_codespace

codespace = resolve_codespace(ctx.codespace_registry, name)
```

**2. Codespace Startup**

Always start the codespace before SSH operations to avoid connection failures:

```python
ctx.codespace.start_codespace(codespace.gh_name)
```

This is a no-op if already running.

**3. Command Building**

Pass the erk CLI string to the builder:

```python
remote_cmd = build_codespace_run_command("erk objective replan 42")
```

The builder handles all environment setup automatically.

**4. SSH Execution**

Use the gateway to execute the remote command:

```python
exit_code = ctx.codespace.run_ssh_command(codespace.gh_name, remote_cmd)
```

## Composability

**Single function for all future remote commands:**

The `build_codespace_run_command()` function is designed for reuse. Every new remote command should use it rather than duplicating environment setup logic.

**No duplication:**

- Environment setup (git pull, uv sync, venv activation) is handled once
- Consistent behavior across all remote commands
- Single place to fix bugs or add features

**Example extensions:**

```python
# Remote replan
remote_cmd = build_codespace_run_command(f"erk objective replan {issue_ref}")

# Remote plan implementation
remote_cmd = build_codespace_run_command(f"erk plan implement {issue_num}")

# Any erk CLI command
remote_cmd = build_codespace_run_command("erk plan list --status pending")
```

## Debugging

### Immediate Failures

**SSH connection failures** are reported immediately with non-zero exit code:

```
Error: Failed to connect to codespace 'my-codespace'
```

**Codespace start failures** cause non-zero exit code before SSH attempt.

### Execution Failures

**Runtime errors** during execution are captured in `/tmp/erk-run.log` on the codespace.

**To diagnose:**

1. SSH to codespace: `erk codespace connect`
2. Check logs: `cat /tmp/erk-run.log`
3. Look for tracebacks, error messages, exit codes

**Log rotation:**

The log file is overwritten on each execution. If you need to preserve logs, copy them before dispatching a new command.

## Future Extensions

### Adding New Remote Commands

**Template checklist:**

- [ ] Create new command file under `src/erk/cli/commands/codespace/run/`
- [ ] Import `build_codespace_run_command` and `resolve_codespace`
- [ ] Follow the 6-step pattern above
- [ ] Add tests following `test_next_plan_cmd.py` pattern
- [ ] Verify gateway calls: `start_codespace()`, `run_ssh_command()`

**Example file structure:**

```
src/erk/cli/commands/codespace/run/
├── __init__.py
├── next_plan_cmd.py          # Existing: erk codespace run objective next-plan
└── replan_cmd.py             # Future: erk codespace run objective replan
```

### Pattern for Any Remote Command

This pattern works for **any** erk CLI operation needing remote execution:

1. Determine the erk CLI string to execute
2. Pass it to `build_codespace_run_command()`
3. Dispatch via SSH with `run_ssh_command()`

No special handling needed for different command types.

## Related Documentation

- [Codespace Gateway](../gateway/codespace-gateway.md) - Gateway ABC and `start_codespace()` method
- [Composable Remote Commands](../architecture/composable-remote-commands.md) - Architecture pattern for reuse
- [Codespace Resolution Helper](../cli/codespace-patterns.md) - `resolve_codespace()` usage

## Source Attribution

**Established in:**

- Plan #6396: `[erk-plan] erk codespace run objective next-plan ISSUE_REF`
- PR #6408: Add `erk codespace run objective next-plan` for remote execution
- Session analysis from implementation

**Implementation location:**

- Command builder: `src/erk/core/codespace_run.py`
- Example command: `src/erk/cli/commands/codespace/run/next_plan_cmd.py`
- Tests: `tests/unit/cli/commands/codespace/run/test_next_plan_cmd.py`
