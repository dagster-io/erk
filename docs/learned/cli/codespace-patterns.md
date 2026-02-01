---
title: Codespace Patterns
read_when:
  - "implementing CLI commands that use codespaces"
  - "working with resolve_codespace() helper"
  - "handling codespace name resolution errors"
---

# Codespace Patterns

Common patterns for working with codespaces in erk CLI commands.

## resolve_codespace() Helper

The `resolve_codespace()` function handles codespace name resolution with proper error handling:

```python
from erk.cli.commands.codespace.resolve import resolve_codespace

codespace = resolve_codespace(ctx.codespace_registry, name)
```

### Function Signature

```python
def resolve_codespace(
    registry: CodespaceRegistry,
    name: str | None
) -> RegisteredCodespace:
    """Resolve a codespace by name or fall back to the default.

    Args:
        registry: The codespace registry to look up from
        name: Codespace name to look up, or None for default

    Returns:
        The resolved RegisteredCodespace

    Raises:
        SystemExit: If the codespace is not found
    """
```

### Resolution Logic

1. **If name is provided**: Look up by name
   - If not found: Display error and exit
2. **If name is None**: Use default codespace
   - If default exists: Return it
   - If default not found: Display error and exit
   - If no default set: Display error and exit

All error paths include a helpful message: `"Use 'erk codespace setup' to create one."`

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

## RegisteredCodespace Fields

The returned `RegisteredCodespace` provides:

- **`name`**: User-friendly short name (e.g., `"work"`)
- **`gh_name`**: Full GitHub codespace name (e.g., `"schrockn-erk-abc123"`)
- **`is_default`**: Whether this is the default codespace

Use `gh_name` for all GitHub CLI operations, and `name` for user-facing messages.

## Related Documentation

- [Composable Remote Commands](../architecture/composable-remote-commands.md) - Template for remote commands using resolve_codespace()
- [Codespace Gateway](../gateway/codespace-gateway.md) - Gateway operations using gh_name
- [Codespace Remote Execution](../erk/codespace-remote-execution.md) - Fire-and-forget pattern
