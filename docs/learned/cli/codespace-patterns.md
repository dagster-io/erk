---
title: Codespace Patterns
last_audited: "2026-02-04 05:48 PT"
audit_result: edited
read_when:
  - "implementing CLI commands that use codespaces"
  - "working with resolve_codespace() helper"
  - "handling codespace name resolution errors"
---

# Codespace Patterns

Common patterns for working with codespaces in erk CLI commands.

## resolve_codespace() Helper

**Source**: `src/erk/cli/commands/codespace/resolve.py`

Resolves a codespace by name or falls back to the default. Takes a `CodespaceRegistry` and optional name, returns `RegisteredCodespace` or exits with a helpful error.

## Error Handling

The helper provides three distinct error messages:

### 1. Named codespace not found

```
Error: No codespace named 'mycodespace' not found.

Use 'erk codespace setup' to create one.
```

Exits with code 1.

### 2. Default codespace not found

```
Error: Default codespace 'old-codespace' not found.

Use 'erk codespace setup' to create one.
```

This happens when a default was set but the codespace was deleted.

### 3. No default set

```
Error: No default codespace set.

Use 'erk codespace setup' to create one.
```

## Usage in Commands

### Pattern: Optional --codespace flag

```python
@click.command("connect")
@click.option("--codespace", "-c", "name", default=None, help="Codespace name.")
@click.pass_obj
def connect(ctx: ErkContext, name: str | None) -> None:
    """Connect to a codespace.

    If --codespace is not provided, uses the default codespace.
    """
    codespace = resolve_codespace(ctx.codespace_registry, name)

    # Use codespace.gh_name for gh CLI commands
    # Use codespace.name for display to user
    click.echo(f"Connecting to '{codespace.name}'...")
```

### Pattern: Required codespace name

If you want to require an explicit name instead of allowing default:

```python
@click.command("remove")
@click.argument("name")
@click.pass_obj
def remove(ctx: ErkContext, name: str) -> None:
    """Remove a codespace from the registry.

    NAME is the codespace name (not GitHub name).
    """
    codespace = resolve_codespace(ctx.codespace_registry, name)
    # ...
```

## RegisteredCodespace Usage

Use `gh_name` for all GitHub CLI operations, and `name` for user-facing messages. Read the dataclass in source for current fields.

## Codespace Setup Command Flow

The `erk codespace setup` command creates a new codespace via REST API, bypassing the broken machines endpoint.

### REST API Creation Flow

The setup command fetches the repository ID via `gh api repos/{owner}/{repo} --jq .id`, then creates the codespace via `POST /user/codespaces` with `repository_id`. This bypasses the broken machines endpoint (HTTP 500 for certain repositories).

**Implementation**: See `src/erk/cli/commands/codespace/setup_cmd.py`.

### Default Machine Type

```python
DEFAULT_MACHINE_TYPE = "basicLinux32gb"
```

Used when no machine type is explicitly specified.

**Why this works**: The `POST /user/codespaces` endpoint accepts `repository_id` as an alternative to repository name, bypassing the broken machines endpoint entirely.

**Code reference**: `src/erk/cli/commands/codespace/setup_cmd.py`

**Related**: [GitHub CLI Limits](../architecture/github-cli-limits.md) - Machines endpoint HTTP 500 bug details

## Related Documentation

- [GitHub CLI Limits](../architecture/github-cli-limits.md) - Machines endpoint HTTP 500 bug and workaround
- [GitHub API Diagnostics](../architecture/github-api-diagnostics.md) - Repository-specific API diagnostic methodology
- [Composable Remote Commands](../architecture/composable-remote-commands.md) - Template for remote commands using resolve_codespace()
- [Codespace Gateway](../gateway/codespace-gateway.md) - Gateway operations using gh_name
- [Codespace Remote Execution](../erk/codespace-remote-execution.md) - Fire-and-forget pattern
