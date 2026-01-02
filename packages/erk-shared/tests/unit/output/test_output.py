"""Tests for output utilities."""

import click
from click.testing import CliRunner

from erk_shared.output.output import user_confirm


@click.command()
@click.option("--default", type=click.Choice(["true", "false", "none"]))
def _confirm_test_command(default: str) -> None:
    """Test command that wraps user_confirm for testing."""
    default_value: bool | None
    if default == "true":
        default_value = True
    elif default == "false":
        default_value = False
    else:
        default_value = None

    result = user_confirm("Continue?", default=default_value)
    click.echo(f"result={result}")


class TestUserConfirm:
    """Tests for user_confirm function."""

    def test_user_confirm_returns_true_on_y_input(self) -> None:
        """Verify user_confirm returns True when user types 'y'."""
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(_confirm_test_command, ["--default", "false"], input="y\n")

        assert result.exit_code == 0
        assert "result=True" in result.output

    def test_user_confirm_returns_false_on_n_input(self) -> None:
        """Verify user_confirm returns False when user types 'n'."""
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(_confirm_test_command, ["--default", "false"], input="n\n")

        assert result.exit_code == 0
        assert "result=False" in result.output

    def test_user_confirm_uses_default_false_on_empty_input(self) -> None:
        """Verify user_confirm uses default=False when user just presses enter."""
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(_confirm_test_command, ["--default", "false"], input="\n")

        assert result.exit_code == 0
        assert "result=False" in result.output

    def test_user_confirm_uses_default_true_on_empty_input(self) -> None:
        """Verify user_confirm uses default=True when user just presses enter."""
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(_confirm_test_command, ["--default", "true"], input="\n")

        assert result.exit_code == 0
        assert "result=True" in result.output

    def test_user_confirm_prompts_on_stderr(self) -> None:
        """Verify user_confirm outputs prompt to stderr (err=True)."""
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(_confirm_test_command, ["--default", "false"], input="y\n")

        assert result.exit_code == 0
        # The prompt goes to stderr, result output goes to stdout
        assert "Continue?" in result.stderr
        assert "result=True" in result.output
