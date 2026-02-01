---
title: Composable Remote Commands Pattern
read_when:
  - "adding a new remote command to run on codespaces"
  - "implementing erk codespace run subcommands"
  - "working with fire-and-forget remote execution"
---

# Composable Remote Commands Pattern

Erk provides a composable pattern for adding new commands that run remotely on GitHub Codespaces. Each remote command follows the same structure and uses shared utilities.

## The Template

Here's the complete template for a new remote command:

```python
"""Run <your-command> remotely on a codespace."""

import click

from erk.cli.commands.codespace.resolve import resolve_codespace
from erk.core.codespace_run import build_codespace_run_command
from erk.core.context import ErkContext


@click.command("<command-name>")
@click.argument("your_arg")
@click.option("--codespace", "-c", "name", default=None, help="Codespace name.")
@click.pass_obj
def run_your_command(ctx: ErkContext, your_arg: str, name: str | None) -> None:
    """Run <your-command> remotely on a codespace.

    YOUR_ARG is a description of the argument.

    Starts the codespace if stopped, then executes 'erk <your-command>'
    in the background via SSH. The command returns immediately (fire-and-forget).
    """
    # 1. Resolve codespace by name or default
    codespace = resolve_codespace(ctx.codespace_registry, name)

    # 2. Start the codespace if stopped
    click.echo(f"Starting codespace '{codespace.name}'...", err=True)
    ctx.codespace.start_codespace(codespace.gh_name)

    # 3. Build the remote command
    remote_cmd = build_codespace_run_command(f"erk <your-command> {your_arg}")

    # 4. Execute remotely
    click.echo(f"Running 'erk <your-command> {your_arg}' on '{codespace.name}'...", err=True)
    exit_code = ctx.codespace.run_ssh_command(codespace.gh_name, remote_cmd)

    # 5. Report results
    if exit_code == 0:
        click.echo("Command dispatched successfully.", err=True)
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
remote_cmd = build_codespace_run_command(f"erk <your-command> {your_arg}")
```

Wraps the erk CLI command with environment bootstrap (git pull, uv sync, venv activation) and background execution (nohup). See [Codespace Remote Execution](../erk/codespace-remote-execution.md) for details.

### 4. Execute Remotely

```python
exit_code = ctx.codespace.run_ssh_command(codespace.gh_name, remote_cmd)
```

Runs the SSH command and returns immediately (fire-and-forget). Output goes to `/tmp/erk-run.log` on the codespace.

### 5. Report Results

```python
if exit_code == 0:
    click.echo("Command dispatched successfully.", err=True)
else:
    click.echo(f"Error: SSH command exited with code {exit_code}.", err=True)
    raise SystemExit(exit_code)
```

Exit code 0 means the SSH connection succeeded and the background process started - NOT that the erk command succeeded.

## Example: erk codespace run objective next-plan

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

    remote_cmd = build_codespace_run_command(f"erk objective next-plan {issue_ref}")
    click.echo(f"Running 'erk objective next-plan {issue_ref}' on '{codespace.name}'...", err=True)
    exit_code = ctx.codespace.run_ssh_command(codespace.gh_name, remote_cmd)

    if exit_code == 0:
        click.echo("Command dispatched successfully.", err=True)
    else:
        click.echo(f"Error: SSH command exited with code {exit_code}.", err=True)
        raise SystemExit(exit_code)
```

## Adding a New Remote Command

1. **Create the command file** under `src/erk/cli/commands/codespace/run/`
2. **Copy the template** and fill in your command name and arguments
3. **Register the command** in the appropriate Click group
4. **Test locally first** - ensure `erk <your-command>` works before making it remote
5. **Test remote execution** - verify output appears in `/tmp/erk-run.log`

## Limitations

- **No output capture**: You can't get stdout/stderr directly
- **No success verification**: Exit code 0 means SSH succeeded, not that the command succeeded
- **No interactive commands**: Commands must run non-interactively

For commands that need output or interactivity, use `ctx.codespace.exec_ssh_interactive()` instead.

## Related Documentation

- [Codespace Remote Execution](../erk/codespace-remote-execution.md) - Fire-and-forget pattern details
- [Codespace Gateway](../gateway/codespace-gateway.md) - Gateway ABC for codespace operations
- [Codespace Patterns](../cli/codespace-patterns.md) - `resolve_codespace()` helper usage
