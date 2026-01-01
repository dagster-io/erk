"""Unit tests for tripwires_reminder_hook command.

These tests use ErkContext.for_test() injection. The .erk/ directory
is created in tmp_path to mark it as a managed project.
"""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.tripwires_reminder_hook import (
    tripwires_reminder_hook,
)
from erk_shared.context.context import ErkContext


def test_tripwires_reminder_hook_outputs_reminder(tmp_path: Path) -> None:
    """Test that hook outputs the expected tripwires reminder message."""
    runner = CliRunner()

    # Create .erk/ to mark as managed project
    (tmp_path / ".erk").mkdir()

    ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
    result = runner.invoke(tripwires_reminder_hook, obj=ctx)

    assert result.exit_code == 0
    assert "tripwires" in result.output
    assert "docs/learned/tripwires.md" in result.output


def test_tripwires_reminder_hook_exits_successfully(tmp_path: Path) -> None:
    """Test that hook exits with code 0."""
    runner = CliRunner()

    # Create .erk/ to mark as managed project
    (tmp_path / ".erk").mkdir()

    ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
    result = runner.invoke(tripwires_reminder_hook, obj=ctx)

    assert result.exit_code == 0


def test_tripwires_reminder_hook_silent_when_not_in_managed_project(
    tmp_path: Path,
) -> None:
    """Test that hook produces no output when not in a managed project."""
    runner = CliRunner()

    # No .erk/ directory - NOT a managed project
    ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
    result = runner.invoke(tripwires_reminder_hook, obj=ctx)

    assert result.exit_code == 0
    assert result.output == ""
