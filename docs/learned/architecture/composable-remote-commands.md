---
title: Composable Remote Commands Pattern
read_when:
  - "adding a new remote command to run on codespaces"
  - "implementing erk codespace run subcommands"
  - "working with streaming remote execution"
---

# Composable Remote Commands Pattern

Erk provides a composable pattern for adding new commands that run remotely on GitHub Codespaces. Each remote command follows the same structure and uses shared utilities.

## The Template

Here's the complete template for a new remote command:

```python
"""Run <your-command> remotely on a codespace."""

import click

from erk.cli.commands.codespace.resolve import resolve_codespace
from erk.core.codespace_run import build_codespace_ssh_command
from erk.core.context import ErkContext


@click.command("<command-name>")
@click.argument("your_arg")
@click.option("--codespace", "-c", "name", default=None, help="Codespace name.")
@click.pass_obj
def run_your_command(ctx: ErkContext, your_arg: str, name: str | None) -> None:
    """Run <your-command> remotely on a codespace.

    YOUR_ARG is a description of the argument.

    Starts the codespace if stopped, then executes 'erk <your-command>'
    via SSH, streaming output to the terminal.
    """
    # 1. Resolve codespace by name or default
    codespace = resolve_codespace(ctx.codespace_registry, name)

    # 2. Start the codespace if stopped
    click.echo(f"Starting codespace '{codespace.name}'...", err=True)
    ctx.codespace.start_codespace(codespace.gh_name)

    # 3. Build the remote command
    remote_cmd = build_codespace_ssh_command(f"erk <your-command> {your_arg}")

    # 4. Execute remotely
    click.echo(f"Running 'erk <your-command> {your_arg}' on '{codespace.name}'...", err=True)
    exit_code = ctx.codespace.run_ssh_command(codespace.gh_name, remote_cmd)

    # 5. Report results
    if exit_code == 0:
        click.echo("Command completed successfully.", err=True)
    else:
        click.echo(f"Error: SSH command exited with code {exit_code}.", err=True)
        raise SystemExit(exit_code)
```

## Step-by-Step Breakdown

### 1. Resolve Codespace

```python
codespace = resolve_codespace(ctx.codespace_registry, name)
```

The `resolve_codespace()` helper handles:

- Looking up codespace by name if provided
- Falling back to default codespace if no name given
- Displaying helpful error messages if not found
- See [Codespace Patterns](../cli/codespace-patterns.md) for details

### 2. Start Codespace

```python
ctx.codespace.start_codespace(codespace.gh_name)
```

Ensures the codespace is running before SSH connection. No-op if already running.

### 3. Build Remote Command

```python
remote_cmd = build_codespace_ssh_command(f"erk <your-command> {your_arg}")
```

Wraps the erk CLI command with environment bootstrap (git pull, uv sync, venv activation) and foreground execution. See [Codespace Remote Execution](../erk/codespace-remote-execution.md) for details.

### 4. Execute Remotely

```python
exit_code = ctx.codespace.run_ssh_command(codespace.gh_name, remote_cmd)
```

Runs the SSH command in the foreground, streaming output to the terminal. The command blocks until completion.

### 5. Report Results

```python
if exit_code == 0:
    click.echo("Command completed successfully.", err=True)
else:
    click.echo(f"Error: SSH command exited with code {exit_code}.", err=True)
    raise SystemExit(exit_code)
```

Exit code reflects the actual erk command's success or failure.

## For Interactive Commands: Using exec_ssh_interactive()

When commands require real-time terminal control (TUI applications, Claude sessions, interactive prompts), use `exec_ssh_interactive()` instead of `run_ssh_command()`.

### Interactive Template

```python
"""Run <your-interactive-command> remotely on a codespace."""

import click

from erk.cli.commands.codespace.resolve import resolve_codespace
from erk.core.codespace_run import build_codespace_ssh_command
from erk.core.context import ErkContext


@click.command("<command-name>")
@click.argument("your_arg")
@click.option("--codespace", "-c", "name", default=None, help="Codespace name.")
@click.pass_obj
def run_your_command(ctx: ErkContext, your_arg: str, name: str | None) -> None:
    """Run <your-interactive-command> remotely on a codespace.

    YOUR_ARG is a description of the argument.

    Starts the codespace if stopped, then executes 'erk <your-command>'
    via SSH with interactive terminal streaming.
    """
    # 1. Resolve codespace by name or default
    codespace = resolve_codespace(ctx.codespace_registry, name)

    # 2. Start the codespace if stopped
    click.echo(f"Starting codespace '{codespace.name}'...", err=True)
    ctx.codespace.start_codespace(codespace.gh_name)

    # 3. Build the remote command
    remote_cmd = build_codespace_ssh_command(f"erk <your-command> {your_arg}")

    # 4. Execute remotely with process replacement (NEVER RETURNS)
    click.echo(f"Running 'erk <your-command> {your_arg}' on '{codespace.name}'...", err=True)
    ctx.codespace.exec_ssh_interactive(codespace.gh_name, remote_cmd)

    # NO CODE AFTER THIS LINE EXECUTES (process replaced)
```

### Key Differences from Non-Interactive Pattern

| Aspect               | Non-Interactive (`run_ssh_command`)           | Interactive (`exec_ssh_interactive`)     |
| -------------------- | --------------------------------------------- | ---------------------------------------- |
| **Return type**      | `int` (exit code)                             | `NoReturn` (process replaced)            |
| **Terminal control** | No TTY allocation, output may buffer          | Full TTY via `-t` flag, real-time output |
| **Exit handling**    | Can check exit code, show completion messages | No post-execution code possible          |
| **Use cases**        | Setup commands, non-interactive scripts       | Claude sessions, TUI apps, vim           |
| **Process model**    | Subprocess, Python continues after            | `os.execvp()`, Python process replaced   |

### When to Use Interactive

Use `exec_ssh_interactive()` when:

- Command requires user input (prompts, TUI navigation)
- Output must stream in real-time (long-running Claude sessions)
- Command launches interactive applications (vim, Claude, etc.)
- Buffering would make it appear to "hang"

**Historical example:** Issue #6514 - `erk codespace run objective next-plan` used `run_ssh_command()`, causing output to appear buffered and the command to hang. Fixed by switching to `exec_ssh_interactive()` (PR #6515).

### Interactive-Specific Considerations

1. **No exit code handling**: Process is replaced, so no exit code is available
2. **No completion messages**: Cannot print "Command completed successfully" after the call
3. **Testing changes**: Must verify `fake.exec_called is True` instead of checking exit codes
4. **All cleanup before call**: Any resource cleanup must happen before `exec_ssh_interactive()`

### Comparison Table: Template Selection

| Question                                   | Answer | Use Template    |
| ------------------------------------------ | ------ | --------------- |
| Does command need real-time terminal I/O?  | Yes    | Interactive     |
| Does command launch TUI applications?      | Yes    | Interactive     |
| Do you need to check exit code afterward?  | Yes    | Non-Interactive |
| Do you need completion messages?           | Yes    | Non-Interactive |
| Is this a setup/config command?            | Yes    | Non-Interactive |
| Will buffering cause "hanging" appearance? | Yes    | Interactive     |

## Example: erk codespace run objective next-plan (Interactive)

Real implementation at `src/erk/cli/commands/codespace/run/objective/next_plan_cmd.py`:

```python
@click.command("next-plan")
@click.argument("issue_ref")
@click.option("--codespace", "-c", "name", default=None, help="Codespace name.")
@click.pass_obj
def run_next_plan(ctx: ErkContext, issue_ref: str, name: str | None) -> None:
    """Run objective next-plan remotely on a codespace.

    ISSUE_REF is an objective issue number or GitHub URL.
    """
    codespace = resolve_codespace(ctx.codespace_registry, name)

    click.echo(f"Starting codespace '{codespace.name}'...", err=True)
    ctx.codespace.start_codespace(codespace.gh_name)

    remote_cmd = build_codespace_ssh_command(f"erk objective next-plan {issue_ref}")
    click.echo(f"Running 'erk objective next-plan {issue_ref}' on '{codespace.name}'...", err=True)

    # Uses interactive method for real-time Claude session streaming
    ctx.codespace.exec_ssh_interactive(codespace.gh_name, remote_cmd)
    # No code after this line - process replaced
```

**Why interactive?** This command launches a Claude Code session for plan implementation. Real-time terminal streaming is essential - buffered output would make it appear to hang during the potentially long-running session.

## Adding a New Remote Command

1. **Create the command file** under `src/erk/cli/commands/codespace/run/`
2. **Copy the template** and fill in your command name and arguments
3. **Register the command** in the appropriate Click group
4. **Test locally first** - ensure `erk <your-command>` works before making it remote
5. **Test remote execution** - verify output streams to your terminal

## Choosing the Right Pattern

### Use Non-Interactive Pattern When:

- Command completes quickly (< 30 seconds)
- Exit code handling is important
- Post-execution messages are needed
- Output buffering is acceptable
- Examples: git operations, configuration commands

### Use Interactive Pattern When:

- Command requires user input
- Real-time output streaming is critical
- Command launches TUI applications
- Long-running sessions (Claude, vim)
- Buffering would cause confusion
- Examples: Claude sessions, interactive debuggers

## Related Documentation

- [Codespace Remote Execution](../erk/codespace-remote-execution.md) - Streaming execution pattern details
- [Codespace Gateway](../gateway/codespace-gateway.md) - Gateway ABC for codespace operations
- [Codespace Patterns](../cli/codespace-patterns.md) - `resolve_codespace()` helper usage
