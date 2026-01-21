"""Codespace execution for isolated implementation mode.

This module provides utilities for running Claude Code inside a GitHub Codespace
with filesystem isolation. The codespace provides a remote execution environment
that makes --dangerously-skip-permissions safe to use.

Key design:
- Resolves codespace from registry (by name or default)
- Uses Codespace gateway for SSH execution (testable)
- Always uses --dangerously-skip-permissions (isolation provides safety)
- Follows the docker_executor.py pattern for consistency
"""

from typing import NoReturn

import click

from erk_shared.core.codespace_registry import CodespaceRegistry, RegisteredCodespace
from erk_shared.gateway.codespace.abc import Codespace


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
    command_arg: str | None,
) -> str:
    """Build the remote command to execute in the codespace.

    Args:
        interactive: Whether running in interactive mode
        model: Optional model name (haiku, sonnet, opus)
        command: Slash command to execute
        command_arg: Optional argument to append to the command (e.g., issue number or file path)

    Returns:
        The complete remote command string
    """
    # Setup: pull latest code and activate virtualenv before running claude
    # (assumes codespace has been set up with uv sync)
    setup_commands = "git pull && source .venv/bin/activate 2>/dev/null || true"

    # Build claude command - always use --dangerously-skip-permissions
    # since codespace provides isolation
    claude_args = ["claude", "--dangerously-skip-permissions"]

    if not interactive:
        claude_args.extend(["--print", "--verbose", "--output-format", "stream-json"])

    if model is not None:
        claude_args.extend(["--model", model])

    # Build the full command with optional argument
    full_command = command if command_arg is None else f"{command} {command_arg}"
    claude_args.append(f'"{full_command}"')

    claude_cmd = " ".join(claude_args)

    # Wrap in bash -l -c to use login shell (ensures PATH includes ~/.claude/local/)
    return f"bash -l -c '{setup_commands} && {claude_cmd}'"


def execute_codespace_interactive(
    *,
    codespace_gateway: Codespace,
    codespace: RegisteredCodespace,
    model: str | None,
    command_arg: str | None,
) -> NoReturn:
    """Execute Claude in codespace interactively, replacing current process.

    Args:
        codespace_gateway: Codespace gateway for SSH execution
        codespace: The registered codespace to use
        model: Optional model name
        command_arg: Optional argument to pass to /erk:plan-implement (issue number or file path)

    Note:
        This function never returns - process is replaced.
    """
    remote_command = build_remote_command(
        interactive=True,
        model=model,
        command="/erk:plan-implement",
        command_arg=command_arg,
    )

    click.echo(f"Launching Claude in codespace '{codespace.name}'...", err=True)

    codespace_gateway.exec_ssh_interactive(codespace.gh_name, remote_command)


def execute_codespace_non_interactive(
    *,
    codespace_gateway: Codespace,
    codespace: RegisteredCodespace,
    model: str | None,
    commands: list[str],
    verbose: bool,
    command_arg: str | None,
) -> int:
    """Execute Claude commands in codespace non-interactively.

    Args:
        codespace_gateway: Codespace gateway for SSH execution
        codespace: The registered codespace to use
        model: Optional model name
        commands: List of slash commands to execute
        verbose: Whether to show verbose output
        command_arg: Optional argument for the first command (issue number or file path)

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    for i, command in enumerate(commands):
        # Only pass command_arg to the first command (/erk:plan-implement)
        arg_for_command = command_arg if i == 0 else None
        remote_command = build_remote_command(
            interactive=False,
            model=model,
            command=command,
            command_arg=arg_for_command,
        )

        if verbose:
            click.echo(f"Running {command} in codespace '{codespace.name}'...", err=True)

        exit_code = codespace_gateway.run_ssh_command(codespace.gh_name, remote_command)

        if exit_code != 0:
            click.echo(
                f"Command {command} failed with exit code {exit_code}",
                err=True,
            )
            return exit_code

    return 0
