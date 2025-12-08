"""Unit tests for tripwires_reminder_hook command."""

from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.tripwires_reminder_hook import (
    tripwires_reminder_hook,
)


def test_tripwires_reminder_hook_outputs_reminder() -> None:
    """Test that hook outputs the expected tripwires reminder message."""
    runner = CliRunner()
    result = runner.invoke(tripwires_reminder_hook)

    assert result.exit_code == 0
    assert "tripwires" in result.output
    assert "After you write code" in result.output


def test_tripwires_reminder_hook_exits_successfully() -> None:
    """Test that hook exits with code 0."""
    runner = CliRunner()
    result = runner.invoke(tripwires_reminder_hook)

    assert result.exit_code == 0
