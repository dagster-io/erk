"""Unit tests for land_execute exec script.

Tests for the `erk exec land-execute` command which executes deferred
land operations from activation scripts.

Most comprehensive tests are in tests/commands/land/ which test the
full workflow. These tests verify basic command registration and argument parsing.
"""

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.land_execute import land_execute
from erk_shared.context.context import ErkContext


def test_land_execute_requires_pr_number() -> None:
    """Test that --pr-number is required."""
    runner = CliRunner()
    ctx = ErkContext.for_test()

    result = runner.invoke(
        land_execute,
        ["--branch=feature-1"],
        obj=ctx,
    )

    assert result.exit_code == 2
    assert "Missing option '--pr-number'" in result.output


def test_land_execute_requires_branch() -> None:
    """Test that --branch is required."""
    runner = CliRunner()
    ctx = ErkContext.for_test()

    result = runner.invoke(
        land_execute,
        ["--pr-number=123"],
        obj=ctx,
    )

    assert result.exit_code == 2
    assert "Missing option '--branch'" in result.output


def test_land_execute_command_registered() -> None:
    """Test that land-execute command is registered in exec group."""
    from erk.cli.commands.exec.group import exec_group

    command_names = [cmd.name for cmd in exec_group.commands.values()]
    assert "land-execute" in command_names
