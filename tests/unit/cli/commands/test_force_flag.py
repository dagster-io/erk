"""Tests for -f shorthand flag presence on --force options."""

from click.testing import CliRunner

from erk.cli.cli import cli


def test_land_command_has_f_shorthand_in_help() -> None:
    """Test that erk land command shows -f shorthand in help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["land", "--help"])

    assert result.exit_code == 0
    assert "-f, --force" in result.output


def test_init_command_has_f_shorthand_in_help() -> None:
    """Test that erk init command shows -f shorthand in help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["init", "--help"])

    assert result.exit_code == 0
    assert "-f, --force" in result.output


def test_artifact_sync_command_has_f_shorthand_in_help() -> None:
    """Test that erk artifact sync command shows -f shorthand in help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["artifact", "sync", "--help"])

    assert result.exit_code == 0
    assert "-f, --force" in result.output
