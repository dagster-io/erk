"""Tests for kit management facade commands."""

from click.testing import CliRunner

from erk.cli.cli import cli


def test_kit_group_accessible() -> None:
    """Kit command group is accessible via erk CLI."""
    runner = CliRunner()
    result = runner.invoke(cli, ["kit", "--help"])
    assert result.exit_code == 0
    assert "Manage kits" in result.output


def test_artifact_group_accessible() -> None:
    """Artifact command group is accessible via erk CLI."""
    runner = CliRunner()
    result = runner.invoke(cli, ["artifact", "--help"])
    assert result.exit_code == 0
    assert "artifact" in result.output.lower()


def test_hook_group_accessible() -> None:
    """Hook command group is accessible via erk CLI."""
    runner = CliRunner()
    result = runner.invoke(cli, ["hook", "--help"])
    assert result.exit_code == 0
    assert "hook" in result.output.lower()


def test_docs_group_accessible() -> None:
    """Docs command group is accessible via erk CLI."""
    runner = CliRunner()
    result = runner.invoke(cli, ["docs", "--help"])
    assert result.exit_code == 0
    assert "docs" in result.output.lower()


def test_help_shows_kit_groups() -> None:
    """Main help shows kit management command groups."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "kit" in result.output
    assert "artifact" in result.output
    assert "hook" in result.output
    assert "docs" in result.output
