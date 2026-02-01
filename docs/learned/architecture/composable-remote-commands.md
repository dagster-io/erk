---
title: Composable Remote Commands Architecture
read_when:
  - "adding new remote execution commands"
  - "building commands that dispatch work to codespaces"
  - "avoiding duplication of environment setup logic"
  - "understanding how to reuse the remote execution framework"
tripwires:
  - action: "adding new erk codespace run commands"
    warning: "Use build_codespace_run_command() for environment setup. Follow pattern: resolve_codespace(), start_codespace(), build_codespace_run_command(), run_ssh_command(). Tests should verify gateway calls and SSH invocation."
---

# Composable Remote Commands Architecture

Remote commands that dispatch work to GitHub Codespaces should reuse the shared execution framework rather than duplicating environment setup logic.

## Problem Solved

**Without pattern:**
- Every new remote command duplicates environment setup (git pull, uv sync, venv activation)
- 15+ lines of boilerplate per command
- Inconsistent setup across commands
- Bug fixes must be applied to multiple locations

**With pattern:**
- Single `build_codespace_run_command()` function handles all setup
- 1-line call per command
- Consistent environment across all remote operations
- Single source of truth for bug fixes and improvements

## The Pattern

### Core Function: `build_codespace_run_command()`

**Location:** `src/erk/core/codespace_run.py`

**Purpose:** Build a complete shell command that sets up the codespace environment and executes an erk CLI command.

**Signature:**

```python
def build_codespace_run_command(cli_command: str) -> str:
    """
    Build a shell command for remote codespace execution.

    Args:
        cli_command: The erk CLI command to execute (e.g., 'erk objective next-plan 42')

    Returns:
        Complete shell command with environment setup and background execution
    """
```

**What it does:**

1. Changes to repository directory: `cd /workspaces/erk`
2. Syncs latest code: `git pull`
3. Installs dependencies: `uv sync`
4. Activates virtual environment: `. .venv/bin/activate`
5. Executes command in background: `nohup <cli_command> > /tmp/erk-run.log 2>&1 &`

**Output:**

```bash
bash -l -c 'cd /workspaces/erk && \
  git pull && \
  uv sync && \
  . .venv/bin/activate && \
  nohup erk objective next-plan 42 > /tmp/erk-run.log 2>&1 &'
```

## Template for New Remote Commands

### File Structure

```
src/erk/cli/commands/codespace/run/
├── __init__.py                # Register subcommands
├── next_plan_cmd.py          # Existing: erk codespace run objective next-plan
└── your_new_cmd.py           # New: erk codespace run <your-command>
```

### Command Template

```python
"""erk codespace run <your-command> implementation."""

import sys
import click
from erk.cli.context import get_command_context
from erk.cli.commands.codespace.helpers import resolve_codespace
from erk.core.codespace_run import build_codespace_run_command
from erk.cli.output import echo


@click.command()
@click.argument("your_arg")  # Adjust as needed
@click.option("--codespace", "-c", help="Codespace name (defaults to configured default)")
@click.pass_context
def your_command_cmd(ctx: click.Context, your_arg: str, codespace: str | None) -> None:
    """Execute 'erk your-command' on a remote codespace."""
    # Step 1: Get command context
    cmd_ctx = get_command_context(ctx)

    # Step 2: Resolve codespace (by name or default)
    cs = resolve_codespace(cmd_ctx.codespace_registry, codespace)

    # Step 3: Start codespace if stopped
    cmd_ctx.codespace.start_codespace(cs.gh_name)

    # Step 4: Build remote command (THE KEY REUSE POINT)
    remote_cmd = build_codespace_run_command(f"erk your-command {your_arg}")

    # Step 5: Execute via SSH
    exit_code = cmd_ctx.codespace.run_ssh_command(cs.gh_name, remote_cmd)

    # Step 6: Report to user
    if exit_code == 0:
        echo(f"✓ Remote execution dispatched for {your_arg}")
        echo("  Check progress: erk codespace connect && tail -f /tmp/erk-run.log")
    else:
        echo(f"✗ Failed to dispatch remote command (exit code {exit_code})")
        sys.exit(exit_code)
```

### Test Template

```python
"""Tests for erk codespace run <your-command>."""

from erk_shared.gateway.codespace import FakeCodespace
from erk.cli.commands.codespace.run.your_new_cmd import your_command_cmd


def test_starts_codespace_before_execution() -> None:
    """Verify codespace is started before SSH command."""
    fake_codespace = FakeCodespace()
    # ... setup context with fake_codespace ...

    # Run command
    result = runner.invoke(your_command_cmd, ["42", "-c", "test-codespace"])

    # Verify start was called
    assert "test-codespace" in fake_codespace.started_codespaces


def test_builds_remote_command_correctly() -> None:
    """Verify correct erk CLI string is passed to builder."""
    fake_codespace = FakeCodespace()
    # ... setup context ...

    result = runner.invoke(your_command_cmd, ["42", "-c", "test-codespace"])

    # Verify SSH command contains expected erk CLI invocation
    ssh_calls = fake_codespace.ssh_commands
    assert len(ssh_calls) == 1
    assert "erk your-command 42" in ssh_calls[0][1]


def test_uses_default_codespace_when_not_specified() -> None:
    """Verify default codespace is used when -c flag omitted."""
    # ... test default resolution ...
```

## Existing Example: `next_plan_cmd.py`

**Command:** `erk codespace run objective next-plan ISSUE_REF`

**Implementation:** `src/erk/cli/commands/codespace/run/next_plan_cmd.py`

**What it does:**
- Dispatches `erk objective next-plan ISSUE_REF` to codespace
- Uses `build_codespace_run_command()` for environment setup
- Returns immediately (fire-and-forget)

**Key code:**

```python
remote_cmd = build_codespace_run_command(f"erk objective next-plan {issue_ref}")
exit_code = cmd_ctx.codespace.run_ssh_command(cs.gh_name, remote_cmd)
```

**Tests:** `tests/unit/cli/commands/codespace/run/test_next_plan_cmd.py`

## Extension Points

### Adding New Commands

**Decision tree:**

1. **Is this an erk CLI command that takes a long time?**
   - Yes → Consider adding remote variant
   - No → Keep as local-only command

2. **Does the user need to see live output?**
   - Yes → Remote execution may not be appropriate (consider streaming alternatives)
   - No → Remote execution is a good fit

3. **Will this command run multiple times in parallel?**
   - Yes → Remote execution enables parallel processing
   - No → Consider if fire-and-forget is valuable

### Future Remote Command Candidates

**Good candidates:**
- `erk codespace run objective replan ISSUE_REF` - long-running replanning
- `erk codespace run plan implement ISSUE_NUM` - remote plan implementation
- `erk codespace run learn ISSUE_REF` - async documentation generation

**Not good candidates:**
- `erk codespace run worktree list` - Fast, needs output
- `erk codespace run config show` - Configuration queries need live output

## Composability Benefits

### Single Source of Truth

**Environment setup in one place:**

```python
# src/erk/core/codespace_run.py
def build_codespace_run_command(cli_command: str) -> str:
    return f"""bash -l -c 'cd /workspaces/erk && \\
      git pull && \\
      uv sync && \\
      . .venv/bin/activate && \\
      nohup {cli_command} > /tmp/erk-run.log 2>&1 &'"""
```

**All remote commands reuse this:**
- Add a dependency? Update once, all commands benefit
- Change log location? Update once, consistent everywhere
- Fix a bug? Fixed for all remote commands immediately

### No Duplication

**Before pattern (hypothetical):**

```python
# In next_plan_cmd.py (15 lines)
remote_cmd = "bash -l -c 'cd /workspaces/erk && git pull && uv sync && ...'"

# In replan_cmd.py (15 lines, duplicated)
remote_cmd = "bash -l -c 'cd /workspaces/erk && git pull && uv sync && ...'"

# In implement_cmd.py (15 lines, duplicated again)
remote_cmd = "bash -l -c 'cd /workspaces/erk && git pull && uv sync && ...'"
```

**With pattern:**

```python
# In next_plan_cmd.py (1 line)
remote_cmd = build_codespace_run_command(f"erk objective next-plan {issue_ref}")

# In replan_cmd.py (1 line)
remote_cmd = build_codespace_run_command(f"erk objective replan {issue_ref}")

# In implement_cmd.py (1 line)
remote_cmd = build_codespace_run_command(f"erk plan implement {issue_num}")
```

### Consistent Behavior

All remote commands get the same:
- Environment setup sequence
- Error handling (via subprocess.run)
- Output logging location
- Background execution semantics

## Integration with Other Patterns

### Codespace Resolution

Use `resolve_codespace()` for consistent name/default lookup:

```python
from erk.cli.commands.codespace.helpers import resolve_codespace

cs = resolve_codespace(cmd_ctx.codespace_registry, codespace_name)
```

See [Codespace Patterns](../cli/codespace-patterns.md) for details.

### Gateway Pattern

Use the `Codespace` gateway for SSH operations:

```python
cmd_ctx.codespace.start_codespace(cs.gh_name)
exit_code = cmd_ctx.codespace.run_ssh_command(cs.gh_name, remote_cmd)
```

See [Codespace Gateway](../gateway/codespace-gateway.md) for details.

### Remote Execution Pattern

The complete pattern (resolution + startup + execution):

```python
cs = resolve_codespace(cmd_ctx.codespace_registry, codespace)
cmd_ctx.codespace.start_codespace(cs.gh_name)
remote_cmd = build_codespace_run_command("erk your-command")
exit_code = cmd_ctx.codespace.run_ssh_command(cs.gh_name, remote_cmd)
```

See [Codespace Remote Execution](../erk/codespace-remote-execution.md) for details.

## Related Documentation

- [Codespace Remote Execution](../erk/codespace-remote-execution.md) - Fire-and-forget execution pattern
- [Codespace Gateway](../gateway/codespace-gateway.md) - Gateway ABC and methods
- [Codespace Patterns](../cli/codespace-patterns.md) - Resolution helper usage

## Source Attribution

**Established in:**
- Plan #6396: `[erk-plan] erk codespace run objective next-plan ISSUE_REF`
- PR #6408: Add `erk codespace run objective next-plan` for remote execution
- Pattern extracted from implementation and tests

**Implementation location:**
- Builder function: `src/erk/core/codespace_run.py`
- Example command: `src/erk/cli/commands/codespace/run/next_plan_cmd.py`
- Example tests: `tests/unit/cli/commands/codespace/run/test_next_plan_cmd.py`
