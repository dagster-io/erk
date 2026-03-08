"""Tests for `erk land --stack` argument validation."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.context import context_for_test
from tests.test_utils.cli_helpers import assert_cli_error


def test_land_rejects_stack_with_up_flag() -> None:
    """`--stack` and `--up` cannot be combined."""
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["land", "--stack", "--up"],
        obj=context_for_test(),
        catch_exceptions=False,
    )

    assert_cli_error(result, 1, "--stack and --up are mutually exclusive")


def test_land_rejects_stack_with_down_flag() -> None:
    """`--stack` and `--down` cannot be combined."""
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["land", "--stack", "--down"],
        obj=context_for_test(),
        catch_exceptions=False,
    )

    assert_cli_error(result, 1, "--stack and --down are mutually exclusive")


def test_land_rejects_stack_with_explicit_target() -> None:
    """`--stack` only works from the current branch."""
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["land", "--stack", "123"],
        obj=context_for_test(),
        catch_exceptions=False,
    )

    assert_cli_error(result, 1, "Cannot use --stack with a PR, URL, or branch argument")
