"""Unit tests for handle_non_ideal_exit decorator and exit_with_error."""

import json

import click
from click.testing import CliRunner

from erk.cli.script_output import exit_with_error, handle_non_ideal_exit
from erk_shared.non_ideal_state import BranchDetectionFailed, NonIdealStateError


# ============================================================================
# Test helpers
# ============================================================================


@click.command()
@handle_non_ideal_exit
def _raises_non_ideal_state() -> None:
    """Test command that raises NonIdealStateError."""
    state = BranchDetectionFailed()
    raise NonIdealStateError(state)


@click.command()
@handle_non_ideal_exit
def _succeeds_normally() -> None:
    """Test command that runs without error."""
    click.echo(json.dumps({"success": True}))


# ============================================================================
# handle_non_ideal_exit
# ============================================================================


def test_handle_non_ideal_exit_catches_error_and_exits_zero() -> None:
    """Decorator catches NonIdealStateError and exits with code 0."""
    runner = CliRunner()
    result = runner.invoke(_raises_non_ideal_state)
    assert result.exit_code == 0


def test_handle_non_ideal_exit_outputs_json_error() -> None:
    """Decorator outputs JSON with success=false and correct error fields."""
    runner = CliRunner()
    result = runner.invoke(_raises_non_ideal_state)
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "branch-detection-failed"
    assert "Could not determine current branch" in output["message"]


def test_handle_non_ideal_exit_does_not_intercept_success() -> None:
    """Decorator does not interfere with commands that succeed."""
    runner = CliRunner()
    result = runner.invoke(_succeeds_normally)
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True


# ============================================================================
# exit_with_error
# ============================================================================


def test_exit_with_error_outputs_json() -> None:
    """exit_with_error outputs structured JSON to stdout."""

    @click.command()
    def _cmd() -> None:
        exit_with_error("some-error", "Something went wrong")

    runner = CliRunner()
    result = runner.invoke(_cmd)
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output == {
        "success": False,
        "error_type": "some-error",
        "message": "Something went wrong",
    }
