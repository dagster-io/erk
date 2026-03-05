"""Unit tests for script_output helpers: envelope helpers and decorators."""

import json

import click
from click.testing import CliRunner

from erk.cli.script_output import (
    dry_run_json,
    error_json,
    exit_with_error,
    handle_non_ideal_exit,
    success_json,
)
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


# ============================================================================
# success_json
# ============================================================================


def test_success_json_outputs_envelope() -> None:
    """success_json outputs JSON with success=true and exits 0."""

    @click.command()
    def _cmd() -> None:
        success_json({"count": 3, "items": ["a", "b", "c"]})

    runner = CliRunner()
    result = runner.invoke(_cmd)
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output == {"success": True, "count": 3, "items": ["a", "b", "c"]}


def test_success_json_merges_kwargs() -> None:
    """success_json merges **kwargs into the envelope."""

    @click.command()
    def _cmd() -> None:
        success_json({"base": 1}, extra="value")

    runner = CliRunner()
    result = runner.invoke(_cmd)
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output == {"success": True, "base": 1, "extra": "value"}


# ============================================================================
# error_json
# ============================================================================


def test_error_json_outputs_envelope() -> None:
    """error_json outputs JSON with success=false and exits 0."""

    @click.command()
    def _cmd() -> None:
        error_json("not-found", "Resource not found")

    runner = CliRunner()
    result = runner.invoke(_cmd)
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output == {
        "success": False,
        "error_type": "not-found",
        "message": "Resource not found",
    }


def test_error_json_merges_details() -> None:
    """error_json merges **details into the envelope."""

    @click.command()
    def _cmd() -> None:
        error_json("validation", "Bad input", field="name")

    runner = CliRunner()
    result = runner.invoke(_cmd)
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["field"] == "name"
    assert output["success"] is False


# ============================================================================
# dry_run_json
# ============================================================================


def test_dry_run_json_outputs_envelope() -> None:
    """dry_run_json outputs JSON with dry_run=true and exits 0."""

    @click.command()
    def _cmd() -> None:
        dry_run_json("create-branch", branch="feature-x")

    runner = CliRunner()
    result = runner.invoke(_cmd)
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output == {
        "success": True,
        "dry_run": True,
        "action": "create-branch",
        "branch": "feature-x",
    }
