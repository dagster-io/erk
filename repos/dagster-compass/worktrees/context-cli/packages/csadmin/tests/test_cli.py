"""Test CLI functionality."""

from click.testing import CliRunner

from csadmin.cli import cli


def test_cli_help() -> None:
    """Test the help command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Compass System Administration CLI" in result.output
