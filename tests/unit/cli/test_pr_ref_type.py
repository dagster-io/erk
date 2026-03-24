"""Tests for PrRefParamType Click parameter type."""

import click
import pytest

from erk.cli.pr_ref_type import PR_REF, PrRefParamType


def test_pr_ref_param_type_converts_plain_number() -> None:
    """Test converting a plain number string."""
    param_type = PrRefParamType()
    result = param_type.convert("123", None, None)
    assert result == 123


def test_pr_ref_param_type_converts_github_url() -> None:
    """Test converting a GitHub PR URL."""
    param_type = PrRefParamType()
    url = "https://github.com/owner/repo/pull/456"
    result = param_type.convert(url, None, None)
    assert result == 456


def test_pr_ref_param_type_converts_graphite_url() -> None:
    """Test converting a Graphite PR URL."""
    param_type = PrRefParamType()
    url = "https://app.graphite.dev/github/pr/owner/repo/789"
    result = param_type.convert(url, None, None)
    assert result == 789


def test_pr_ref_param_type_converts_int_passthrough() -> None:
    """Test that integer values pass through unchanged."""
    param_type = PrRefParamType()
    result = param_type.convert(999, None, None)
    assert result == 999


def test_pr_ref_param_type_fails_on_invalid_input() -> None:
    """Test that invalid input raises BadParameter."""
    param_type = PrRefParamType()
    with pytest.raises(click.exceptions.BadParameter) as exc_info:
        param_type.convert("not-a-pr-ref", None, None)

    assert "'not-a-pr-ref' is not a valid PR reference" in str(exc_info.value)
    assert "Plain number: 123" in str(exc_info.value)
    assert "GitHub URL:" in str(exc_info.value)
    assert "Graphite URL:" in str(exc_info.value)


def test_pr_ref_constant_is_pr_ref_param_type() -> None:
    """Test that PR_REF constant is an instance of PrRefParamType."""
    assert isinstance(PR_REF, PrRefParamType)


def test_pr_ref_param_type_name() -> None:
    """Test that param type has correct name."""
    assert PR_REF.name == "pr_ref"


def test_pr_ref_with_click_command() -> None:
    """Test integration with Click command."""

    @click.command()
    @click.argument("pr", type=PR_REF)
    def test_cmd(pr: int) -> int:
        return pr

    runner = click.testing.CliRunner()

    result = runner.invoke(test_cmd, ["123"])
    assert result.exit_code == 0

    result = runner.invoke(test_cmd, ["https://github.com/owner/repo/pull/456"])
    assert result.exit_code == 0

    result = runner.invoke(test_cmd, ["invalid"])
    assert result.exit_code != 0
    assert "not a valid PR reference" in result.output
