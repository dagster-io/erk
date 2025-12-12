"""Unit tests for tripwires_reminder_hook command."""

from unittest.mock import patch

from click.testing import CliRunner

from erk_kits.data.kits.erk.scripts.erk.tripwires_reminder_hook import (
    tripwires_reminder_hook,
)


def test_tripwires_reminder_hook_outputs_reminder() -> None:
    """Test that hook outputs the expected tripwires reminder message."""
    runner = CliRunner()

    with patch("erk.kits.hooks.decorators.is_in_managed_project", return_value=True):
        result = runner.invoke(tripwires_reminder_hook)

    assert result.exit_code == 0
    assert "tripwires" in result.output
    assert "docs/agent/tripwires.md" in result.output


def test_tripwires_reminder_hook_exits_successfully() -> None:
    """Test that hook exits with code 0."""
    runner = CliRunner()

    with patch("erk.kits.hooks.decorators.is_in_managed_project", return_value=True):
        result = runner.invoke(tripwires_reminder_hook)

    assert result.exit_code == 0


def test_tripwires_reminder_hook_silent_when_not_in_managed_project() -> None:
    """Test that hook produces no output when not in a managed project."""
    runner = CliRunner()

    with patch("erk.kits.hooks.decorators.is_in_managed_project", return_value=False):
        result = runner.invoke(tripwires_reminder_hook)

    assert result.exit_code == 0
    assert result.output == ""
