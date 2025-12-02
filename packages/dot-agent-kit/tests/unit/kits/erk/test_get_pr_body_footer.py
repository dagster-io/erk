"""Unit tests for get_pr_body_footer kit CLI command.

Tests the PR body footer generation for remote implementation PRs.
"""

from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.get_pr_body_footer import (
    get_pr_body_footer,
)


def test_get_pr_body_footer_outputs_checkout_and_graphite_steps() -> None:
    """Test that footer includes checkout command and Graphite steps."""
    runner = CliRunner()

    result = runner.invoke(get_pr_body_footer, ["--pr-number", "1895"])

    assert result.exit_code == 0
    assert "erk pr checkout 1895" in result.output
    assert "If using Graphite" in result.output
    assert "gt track" in result.output
    assert "gt squash && gt submit -f" in result.output
    assert "---" in result.output
    assert "To checkout this PR" in result.output


def test_get_pr_body_footer_requires_pr_number() -> None:
    """Test that --pr-number is required."""
    runner = CliRunner()

    result = runner.invoke(get_pr_body_footer, [])

    assert result.exit_code != 0
    assert "Missing option" in result.output or "required" in result.output.lower()


def test_get_pr_body_footer_different_pr_numbers() -> None:
    """Test that different PR numbers are correctly embedded in output."""
    runner = CliRunner()

    result = runner.invoke(get_pr_body_footer, ["--pr-number", "42"])

    assert result.exit_code == 0
    assert "erk pr checkout 42" in result.output
    assert "1895" not in result.output
