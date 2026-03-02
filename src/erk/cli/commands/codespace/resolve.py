"""Codespace resolution helper.

Shared logic for resolving a codespace by name or default.
Used by both connect and run commands.
"""

import click

from erk_shared.gateway.codespace_registry.abc import CodespaceRegistry, RegisteredCodespace


def resolve_codespace(
    registry: CodespaceRegistry,
    name: str | None,
    *,
    config_codespace_name: str | None,
) -> RegisteredCodespace:
    """Resolve a codespace by name, repo config, or global default.

    Resolution precedence:
    1. Explicit CLI name argument (highest)
    2. Repo config codespace name (from .erk/config.local.toml or .erk/config.toml)
    3. Global default from ~/.erk/codespaces.toml (lowest)

    Args:
        registry: The codespace registry to look up from
        name: Codespace name from CLI argument, or None
        config_codespace_name: Codespace name from repo config, or None

    Returns:
        The resolved RegisteredCodespace

    Raises:
        SystemExit: If the codespace is not found
    """
    # 1. Explicit CLI name
    if name is not None:
        codespace = registry.get(name)
        if codespace is None:
            click.echo(f"Error: No codespace named '{name}' found.", err=True)
            click.echo("\nUse 'erk codespace setup' to create one.", err=True)
            raise SystemExit(1)
        return codespace

    # 2. Repo config codespace name
    if config_codespace_name is not None:
        codespace = registry.get(config_codespace_name)
        if codespace is None:
            click.echo(
                f"Error: Repo config references codespace '{config_codespace_name}' "
                "which is not registered.",
                err=True,
            )
            click.echo("\nUse 'erk codespace setup' to register it.", err=True)
            raise SystemExit(1)
        return codespace

    # 3. Global default
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
