---
title: Codespace CLI Patterns
read_when:
  - "adding new codespace commands that accept -c/--codespace flag"
  - "implementing default codespace resolution logic"
  - "avoiding duplication of codespace lookup code"
  - "providing consistent error messages for missing codespaces"
tripwires:
  - action: "adding new codespace commands with -c/--codespace flag"
    warning: "Use resolve_codespace(registry, name) helper for consistent name/default resolution and error messages. Import from erk.cli.commands.codespace.helpers."
---

# Codespace CLI Patterns

Patterns for building CLI commands that work with GitHub Codespaces.

## Codespace Resolution Helper

### Problem Solved

**Without helper:**

- Each command duplicates 15 lines of codespace lookup logic
- Inconsistent error messages across commands
- Repeated logic for default vs named codespace resolution
- Easy to forget edge cases (default not set, default not found, etc.)

**With helper:**

- 1-line function call: `resolve_codespace(registry, name)`
- Consistent error messages across all codespace commands
- All edge cases handled in one place
- Returns `RegisteredCodespace` ready for use

### The Helper Function

**Location:** `src/erk/cli/commands/codespace/helpers.py`

**Signature:**

```python
def resolve_codespace(
    registry: CodespaceRegistry,
    name: str | None,
) -> RegisteredCodespace:
    """
    Resolve a codespace by name or fall back to the default.

    Args:
        registry: Codespace registry to search
        name: Codespace name (None means use default)

    Returns:
        RegisteredCodespace ready for operations

    Raises:
        SystemExit: If codespace not found (exits with code 1)
    """
```

### Behavior

**When `name` is provided:**

1. Look up codespace by name in registry
2. If found: return it
3. If not found: print error and exit:
   ```
   Error: No codespace named 'my-codespace' found.
   Use 'erk codespace setup' to create one.
   ```

**When `name` is None (use default):**

1. Check if default codespace is configured
2. If not configured: print error and exit:
   ```
   Error: No default codespace set.
   Use 'erk codespace setup' to create one.
   ```
3. If configured but not found in registry: print error and exit:
   ```
   Error: Default codespace 'my-codespace' not found in registry.
   Use 'erk codespace setup' to reconfigure.
   ```
4. If configured and found: return it

### Error Messages

All error messages:

- Are prefixed with "Error: " for clarity
- Include helpful hint: "Use 'erk codespace setup' to create one"
- Exit with code 1 (via `sys.exit(1)`)
- Are consistent across all commands using the helper

## Usage in Commands

### Basic Pattern

```python
import click
from erk.cli.context import get_command_context
from erk.cli.commands.codespace.helpers import resolve_codespace


@click.command()
@click.option("--codespace", "-c", help="Codespace name (defaults to configured default)")
@click.pass_context
def my_command(ctx: click.Context, codespace: str | None) -> None:
    """Do something with a codespace."""
    cmd_ctx = get_command_context(ctx)

    # Step 1: Resolve codespace (by name or default)
    cs = resolve_codespace(cmd_ctx.codespace_registry, codespace)

    # Step 2: Use the resolved codespace
    print(f"Using codespace: {cs.name}")
    print(f"GitHub name: {cs.gh_name}")
```

### With Remote Execution

```python
@click.command()
@click.argument("issue_ref")
@click.option("--codespace", "-c", help="Codespace name (defaults to configured default)")
@click.pass_context
def remote_command(ctx: click.Context, issue_ref: str, codespace: str | None) -> None:
    """Execute remote command on codespace."""
    cmd_ctx = get_command_context(ctx)

    # Resolve codespace
    cs = resolve_codespace(cmd_ctx.codespace_registry, codespace)

    # Start it
    cmd_ctx.codespace.start_codespace(cs.gh_name)

    # Execute remote command
    remote_cmd = build_codespace_run_command(f"erk some-command {issue_ref}")
    exit_code = cmd_ctx.codespace.run_ssh_command(cs.gh_name, remote_cmd)

    if exit_code != 0:
        sys.exit(exit_code)
```

## When to Use This Helper

**Use the helper when:**

- Command accepts optional `-c/--codespace` flag
- Command needs to fall back to default codespace
- Command should provide consistent error messages

**Don't use the helper when:**

- Command requires codespace name (not optional)
- Command operates on all codespaces (iteration)
- Command doesn't interact with codespace registry

## Existing Usage

### 1. `erk codespace connect`

**Before refactor (15 lines):**

```python
def connect_cmd(ctx: click.Context, codespace: str | None) -> None:
    cmd_ctx = get_command_context(ctx)
    registry = cmd_ctx.codespace_registry

    if codespace is not None:
        cs = registry.get(codespace)
        if cs is None:
            echo(f"Error: No codespace named '{codespace}' found.")
            sys.exit(1)
    else:
        default_name = registry.default
        if default_name is None:
            echo("Error: No default codespace set.")
            sys.exit(1)
        cs = registry.get(default_name)
        if cs is None:
            echo(f"Error: Default codespace '{default_name}' not found.")
            sys.exit(1)

    # Now use cs...
```

**After refactor (1 line):**

```python
def connect_cmd(ctx: click.Context, codespace: str | None) -> None:
    cmd_ctx = get_command_context(ctx)
    cs = resolve_codespace(cmd_ctx.codespace_registry, codespace)
    # Now use cs...
```

### 2. `erk codespace run objective next-plan`

**Implementation:** `src/erk/cli/commands/codespace/run/next_plan_cmd.py`

```python
def next_plan_cmd(ctx: click.Context, issue_ref: str, codespace: str | None) -> None:
    cmd_ctx = get_command_context(ctx)
    cs = resolve_codespace(cmd_ctx.codespace_registry, codespace)
    # ... use cs for remote execution ...
```

## For New Commands

### Checklist

When adding a new codespace command:

- [ ] Add `--codespace/-c` option with help text
- [ ] Make the option type `str | None` to support default fallback
- [ ] Call `resolve_codespace(cmd_ctx.codespace_registry, codespace)` early in command
- [ ] Use the returned `RegisteredCodespace` for subsequent operations
- [ ] Don't add custom error handling—the helper handles it

### Command Option Template

```python
@click.option(
    "--codespace",
    "-c",
    type=str,
    default=None,
    help="Codespace name (defaults to configured default)"
)
```

**Important:**

- Type must be `str | None` (not `str`)
- Default must be `None` (to trigger default resolution)
- Help text should mention "defaults to configured default"

## Testing the Helper

### Unit Tests

Test the helper directly:

```python
def test_resolve_by_name() -> None:
    """Resolve codespace by explicit name."""
    cs = RegisteredCodespace(name="test-cs", gh_name="gh-test", ...)
    registry = FakeCodespaceRegistry([cs], default=None)

    result = resolve_codespace(registry, "test-cs")
    assert result.name == "test-cs"


def test_resolve_default() -> None:
    """Resolve codespace via default when name not provided."""
    cs = RegisteredCodespace(name="default-cs", gh_name="gh-default", ...)
    registry = FakeCodespaceRegistry([cs], default="default-cs")

    result = resolve_codespace(registry, None)
    assert result.name == "default-cs"


def test_error_when_name_not_found() -> None:
    """Exit with error when named codespace not found."""
    registry = FakeCodespaceRegistry([], default=None)

    with pytest.raises(SystemExit) as exc_info:
        resolve_codespace(registry, "nonexistent")

    assert exc_info.value.code == 1
```

### Integration in Command Tests

Test that commands use the helper correctly:

```python
def test_uses_default_codespace() -> None:
    """Command uses default when -c flag omitted."""
    # Setup registry with default
    cs = RegisteredCodespace(name="default-cs", gh_name="gh-default", ...)
    registry = FakeCodespaceRegistry([cs], default="default-cs")

    # Run command without -c flag
    result = runner.invoke(my_command, [])

    # Verify default was used
    assert "default-cs" in result.output
```

## Related Documentation

- [Codespace Remote Execution](../erk/codespace-remote-execution.md) - Using resolved codespaces for remote execution
- [Composable Remote Commands](../architecture/composable-remote-commands.md) - Template showing resolution + execution
- [Codespace Gateway](../gateway/codespace-gateway.md) - Gateway operations on resolved codespaces

## Source Attribution

**Established in:**

- Plan #6396: `[erk-plan] erk codespace run objective next-plan ISSUE_REF`
- PR #6408: Add `erk codespace run objective next-plan` for remote execution
- Helper extracted to reduce duplication across codespace commands

**Implementation location:**

- Helper: `src/erk/cli/commands/codespace/helpers.py`
- Usage: `src/erk/cli/commands/codespace/connect_cmd.py`
- Usage: `src/erk/cli/commands/codespace/run/next_plan_cmd.py`
