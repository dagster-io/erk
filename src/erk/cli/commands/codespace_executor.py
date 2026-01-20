"""Codespace execution for isolated implementation mode.

This module provides utilities for running Claude Code inside a GitHub Codespace
with filesystem isolation. The codespace provides a remote execution environment
that makes --dangerously-skip-permissions safe to use.

Key design:
- Resolves codespace from registry (by name or default)
- Uses gh codespace ssh for remote execution
- Always uses --dangerously-skip-permissions (isolation provides safety)
- Follows the docker_executor.py pattern for consistency
"""

import os
import subprocess

import click

from erk_shared.core.codespace_registry import CodespaceRegistry, RegisteredCodespace


class CodespaceNotFoundError(Exception):
    """Raised when a codespace cannot be resolved."""


def resolve_codespace(
    registry: CodespaceRegistry,
    *,
    name: str | None,
) -> RegisteredCodespace:
    """Resolve codespace from registry by name or default.

    Args:
        registry: CodespaceRegistry for looking up codespaces
        name: Optional name of the codespace. If None, uses default.

    Returns:
        The resolved RegisteredCodespace

    Raises:
        CodespaceNotFoundError: If codespace not found or no default set
    """
    if name is not None:
        codespace = registry.get(name)
        if codespace is None:
            raise CodespaceNotFoundError(
                f"No codespace named '{name}' found.\n"
                "Use 'erk codespace list' to see registered codespaces."
            )
        return codespace

    # Use default codespace
    codespace = registry.get_default()
    if codespace is None:
        default_name = registry.get_default_name()
        if default_name is not None:
            raise CodespaceNotFoundError(
                f"Default codespace '{default_name}' not found.\n"
                "Use 'erk codespace list' to see registered codespaces."
            )
        raise CodespaceNotFoundError(
            "No default codespace set.\n"
            "Use 'erk codespace setup <name>' to create one, or\n"
            "Use 'erk codespace set-default <name>' to set one."
        )

    return codespace


def build_remote_command(
    *,
    interactive: bool,
    model: str | None,
    command: str,
) -> str:
    """Build the remote command to execute in the codespace.

    Args:
        interactive: Whether running in interactive mode
        model: Optional model name (haiku, sonnet, opus)
        command: Slash command to execute

    Returns:
        The complete remote command string
    """
    # Setup: activate virtualenv before running claude
    # (assumes codespace has been set up with uv sync)
    setup_commands = "source .venv/bin/activate 2>/dev/null || true"

    # Build claude command - always use --dangerously-skip-permissions
    # since codespace provides isolation
    claude_args = ["claude", "--dangerously-skip-permissions"]

    if not interactive:
        claude_args.extend(["--print", "--verbose", "--output-format", "stream-json"])

    if model is not None:
        claude_args.extend(["--model", model])

    claude_args.append(f'"{command}"')

    claude_cmd = " ".join(claude_args)

    # Wrap in bash -l -c to use login shell (ensures PATH includes ~/.claude/local/)
    return f"bash -l -c '{setup_commands} && {claude_cmd}'"


def execute_codespace_interactive(
    *,
    codespace: RegisteredCodespace,
    model: str | None,
) -> None:
    """Execute Claude in codespace interactively, replacing current process.

    Args:
        codespace: The registered codespace to use
        model: Optional model name

    Note:
        This function never returns - process is replaced.
    """
    remote_command = build_remote_command(
        interactive=True,
        model=model,
        command="/erk:plan-implement",
    )

    click.echo(f"Launching Claude in codespace '{codespace.name}'...", err=True)

    # GH-API-AUDIT: REST - codespace SSH connection
    # -t: Force pseudo-terminal allocation (required for interactive TUI)
    os.execvp(
        "gh",
        [
            "gh",
            "codespace",
            "ssh",
            "-c",
            codespace.gh_name,
            "--",
            "-t",
            remote_command,
        ],
    )
    # Never returns


def execute_codespace_non_interactive(
    *,
    codespace: RegisteredCodespace,
    model: str | None,
    commands: list[str],
    verbose: bool,
) -> int:
    """Execute Claude commands in codespace non-interactively.

    Args:
        codespace: The registered codespace to use
        model: Optional model name
        commands: List of slash commands to execute
        verbose: Whether to show verbose output

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    for command in commands:
        remote_command = build_remote_command(
            interactive=False,
            model=model,
            command=command,
        )

        if verbose:
            click.echo(f"Running {command} in codespace '{codespace.name}'...", err=True)

        # GH-API-AUDIT: REST - codespace SSH connection
        # Note: No -t flag for non-interactive (no TTY allocation)
        result = subprocess.run(
            [
                "gh",
                "codespace",
                "ssh",
                "-c",
                codespace.gh_name,
                "--",
                remote_command,
            ],
            check=False,
        )

        if result.returncode != 0:
            click.echo(
                f"Command {command} failed with exit code {result.returncode}",
                err=True,
            )
            return result.returncode

    return 0
