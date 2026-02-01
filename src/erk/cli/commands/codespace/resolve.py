"""Codespace resolution helper.

Shared logic for resolving a codespace by name or default.
Used by both connect and run commands.
"""

import click

from erk_shared.gateway.codespace_registry.abc import CodespaceRegistry, RegisteredCodespace


def resolve_codespace(registry: CodespaceRegistry, name: str | None) -> RegisteredCodespace:
    """Resolve a codespace by name or fall back to the default.

    Args:
        registry: The codespace registry to look up from
        name: Codespace name to look up, or None for default

    Returns:
        The resolved RegisteredCodespace

    Raises:
        SystemExit: If the codespace is not found
    """
    if name is not None:
        codespace = registry.get(name)
        if codespace is None:
            click.echo(f"Error: No codespace named '{name}' found.", err=True)
            click.echo("\nUse 'erk codespace setup' to create one.", err=True)
            raise SystemExit(1)
        return codespace

    codespace = registry.get_default()
    if codespace is not None:
        return codespace

    default_name = registry.get_default_name()
    if default_name is not None:
        click.echo(f"Error: Default codespace '{default_name}' not found.", err=True)
    else:
        click.echo("Error: No default codespace set.", err=True)
    click.echo("\nUse 'erk codespace setup' to create one.", err=True)
    raise SystemExit(1)
