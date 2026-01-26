---
title: Local/Remote Command Group Pattern
read_when:
  - "creating commands with local and remote variants"
  - "using invoke_without_command=True pattern"
  - "migrating separate commands to a unified group"
---

# Local/Remote Command Group Pattern

This document describes the pattern for commands that have both local and remote execution variants, unified under a single command group.

## Overview

Some erk commands can be executed either:

- **Locally**: Using Claude CLI on the developer's machine
- **Remotely**: Via GitHub Actions workflow

Rather than maintaining separate commands (`erk pr address` and `erk pr address-remote`), we use a command group pattern where:

- The base command runs the local variant
- A `remote` subcommand triggers the GitHub Actions workflow

## The Pattern

### Command Group with Default Behavior

```python
@click.group("address", cls=ErkCommandGroup, invoke_without_command=True)
@click.option("--dangerous", is_flag=True, help="Acknowledge Claude invocation")
@click.pass_context
def address_group(ctx: click.Context, *, dangerous: bool) -> None:
    """Address PR review comments with AI-powered resolution.

    When run without a subcommand, addresses PR review comments on the
    current branch using Claude.

    Use 'erk pr address remote <pr_number>' to trigger remote addressing via
    GitHub Actions workflow.
    """
    if ctx.invoked_subcommand is None:
        # Run local address when no subcommand given
        erk_ctx: ErkContext = ctx.obj
        _run_local_address(erk_ctx, dangerous=dangerous)


@address_group.command("remote")
@click.argument("pr_number", type=int, required=True)
@click.pass_obj
def address_remote(ctx: ErkContext, pr_number: int) -> None:
    """Trigger remote PR review comment addressing."""
    # Trigger GitHub Actions workflow
    ...
```

### Key Elements

1. **`invoke_without_command=True`**: Allows the group itself to execute when no subcommand is given
2. **`ctx.invoked_subcommand is None`**: Check if user called the group directly vs a subcommand
3. **`cls=ErkCommandGroup`**: Uses erk's custom group class for consistent help formatting
4. **Local in group function, remote as subcommand**: The common case (local) is the default

## ErkCommandGroup Helper

`ErkCommandGroup` is a custom Click group class that:

- Organizes commands into logical sections in help output
- Provides consistent formatting across erk CLI
- Supports command grouping in help text

Import from:

```python
from erk.cli.help_formatter import ErkCommandGroup
```

## Usage Examples

```bash
# Local execution (default - no subcommand)
erk pr address --dangerous

# Remote execution (explicit subcommand)
erk pr address remote 123

# Help shows both variants
erk pr address --help
```

## Migration Checklist

When unifying separate local/remote commands into a group:

1. **Identify the existing commands**
   - e.g., `erk pr address` (local) and `erk pr address-remote` (remote)

2. **Create the unified group**
   - Use `@click.group("name", cls=ErkCommandGroup, invoke_without_command=True)`
   - Put local logic in the group function (default behavior)
   - Add remote as a subcommand

3. **Update test invocations**
   - Change `["pr", "address-remote", "123"]` to `["pr", "address", "remote", "123"]`
   - Keep local tests unchanged (they invoke the same command path)

4. **Update documentation**
   - Help text should explain both variants
   - Examples should show both usage patterns

5. **Remove the old separate command**
   - Delete the standalone remote command file
   - Update any imports/registrations

## Reference Implementations

- `src/erk/cli/commands/pr/address_cmd.py` - PR comment addressing
- `src/erk/cli/commands/pr/fix_conflicts_cmd.py` - Conflict resolution
- `src/erk/cli/commands/init/__init__.py` - Project initialization

## Related Documentation

- [CLI Development](index.md) - CLI patterns overview
- [Command Group Testing](../testing/command-group-testing.md) - Testing grouped commands
