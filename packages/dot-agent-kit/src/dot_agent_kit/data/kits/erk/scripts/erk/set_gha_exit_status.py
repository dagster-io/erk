#!/usr/bin/env python3
"""Run a command and capture exit status for GitHub Actions output.

This command runs a specified command, captures its exit code, and writes
both the raw exit code and a boolean success value to GITHUB_OUTPUT.

Usage:
    erk kit exec erk set-gha-exit-status --output-var implementation_success -- claude --print ...

Output:
    JSON object with execution results (also writes to GITHUB_OUTPUT)

Exit Codes:
    0: Always exits 0 (captures inner command's exit code to output)

Examples:
    $ erk kit exec erk set-gha-exit-status --output-var impl_success -- make test
    {
      "success": true,
      "exit_code": 0,
      "output_var": "impl_success",
      "output_value": true
    }

    $ erk kit exec erk set-gha-exit-status --output-var impl_success -- false
    {
      "success": true,
      "exit_code": 1,
      "output_var": "impl_success",
      "output_value": false
    }
"""

import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

import click


class CommandRunner(Protocol):
    """Protocol for running commands."""

    def run(self, command: list[str], cwd: Path) -> int:
        """Run command and return exit code."""
        ...


class RealCommandRunner:
    """Real command runner using subprocess."""

    def run(self, command: list[str], cwd: Path) -> int:
        """Run command and return exit code."""
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
        )
        return result.returncode


@dataclass
class ExitStatusSuccess:
    """Result from running a command and capturing exit status."""

    success: bool
    exit_code: int
    output_var: str
    output_value: bool


def _write_to_github_output(key: str, value: str) -> bool:
    """Write a key=value pair to GITHUB_OUTPUT file.

    Args:
        key: Output variable name
        value: Output value

    Returns:
        True if written successfully, False if GITHUB_OUTPUT not set
    """
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output is None:
        return False

    with open(github_output, "a", encoding="utf-8") as f:
        f.write(f"{key}={value}\n")
    return True


def _set_gha_exit_status_impl(
    runner: CommandRunner,
    cwd: Path,
    output_var: str,
    command: tuple[str, ...],
) -> ExitStatusSuccess:
    """Run command and capture exit status.

    Args:
        runner: Command runner implementation
        cwd: Current working directory
        output_var: Name of output variable for boolean result
        command: Command to execute

    Returns:
        ExitStatusSuccess with exit code and boolean value
    """
    # Run the command and capture exit code
    exit_code = runner.run(list(command), cwd)

    # Derive boolean success value
    output_value = exit_code == 0

    # Write to GITHUB_OUTPUT if available
    _write_to_github_output("exit_code", str(exit_code))
    _write_to_github_output(output_var, str(output_value).lower())

    return ExitStatusSuccess(
        success=True,
        exit_code=exit_code,
        output_var=output_var,
        output_value=output_value,
    )


@click.command(name="set-gha-exit-status")
@click.option("--output-var", required=True, help="Name of output variable for boolean result")
@click.argument("command", nargs=-1, required=True)
@click.pass_context
def set_gha_exit_status(
    ctx: click.Context,
    output_var: str,
    command: tuple[str, ...],
) -> None:
    """Run command and capture exit status.

    Runs the provided command, captures the exit code, and writes both the
    raw exit code and a boolean success value to GITHUB_OUTPUT. Always exits
    with code 0 to allow the workflow to continue.

    The command should be provided after -- to avoid conflicts with options.
    """
    # Get cwd from context if available, otherwise use Path.cwd()
    if ctx.obj is not None and hasattr(ctx.obj, "cwd"):
        cwd = ctx.obj.cwd
    else:
        cwd = Path.cwd()

    # Get runner from context if available (for testing), otherwise use real
    if ctx.obj is not None and hasattr(ctx.obj, "command_runner"):
        runner = ctx.obj.command_runner
    else:
        runner = RealCommandRunner()

    result = _set_gha_exit_status_impl(runner, cwd, output_var, command)

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Always exit 0 - we capture the inner command's exit code, not propagate it
