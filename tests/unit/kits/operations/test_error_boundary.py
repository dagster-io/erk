"""Tests for error boundary and debug mode functionality."""

from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from erk.kits.error_boundary import cli_error_boundary
from erk.kits.sources.exceptions import (
    ArtifactConflictError,
    DotAgentNonIdealStateException,
    InvalidKitIdError,
    KitNotFoundError,
)


def test_error_boundary_custom_exception_without_debug() -> None:
    """Test that custom exceptions show clean messages without debug mode."""

    @click.command()
    @cli_error_boundary
    def cmd() -> None:
        raise KitNotFoundError("test-kit", ["bundled", "package"])

    runner = CliRunner()
    result = runner.invoke(cmd, [])

    assert result.exit_code == 1
    assert "Error: Kit 'test-kit' not found" in result.output
    assert "Traceback" not in result.output
    assert "--debug" not in result.output


def test_error_boundary_custom_exception_with_debug() -> None:
    """Test that custom exceptions show clean messages even with debug mode.

    Custom exceptions are expected errors, so we show clean messages
    rather than stack traces even in debug mode.
    """

    @click.group()
    @click.option("--debug", is_flag=True)
    @click.pass_context
    def cli(ctx: click.Context, debug: bool) -> None:
        ctx.ensure_object(dict)
        ctx.obj["debug"] = debug

    @cli.command()
    @cli_error_boundary
    def cmd() -> None:
        raise InvalidKitIdError("Test_Kit")

    runner = CliRunner()
    result = runner.invoke(cli, ["--debug", "cmd"])

    assert result.exit_code == 1
    assert "Error: Invalid kit ID 'Test_Kit'" in result.output
    # Custom exceptions should show clean message even in debug mode
    assert "must only contain lowercase" in result.output


def test_error_boundary_unexpected_exception_shows_trace() -> None:
    """Test that unexpected exceptions always show full stack traces."""

    @click.command()
    @cli_error_boundary
    def cmd() -> None:
        raise RuntimeError("Something went wrong internally")

    runner = CliRunner()
    result = runner.invoke(cmd, [])

    assert result.exit_code == 1
    assert "Traceback (most recent call last):" in result.output
    assert "RuntimeError: Something went wrong internally" in result.output


def test_error_boundary_debug_flag_propagation_nested_commands() -> None:
    """Test that unexpected exceptions show stack traces in nested command groups."""

    @click.group()
    @click.option("--debug", is_flag=True)
    @click.pass_context
    def cli(ctx: click.Context, debug: bool) -> None:
        ctx.ensure_object(dict)
        ctx.obj["debug"] = debug

    @cli.group()
    @click.pass_context
    def subgroup(ctx: click.Context) -> None:
        pass

    @subgroup.command("nested-cmd")
    @cli_error_boundary
    @click.pass_context
    def nested_cmd(ctx: click.Context) -> None:
        raise ValueError("Unexpected error in nested command")

    runner = CliRunner()

    # Test without debug - still shows stack trace for unexpected exceptions
    result = runner.invoke(cli, ["subgroup", "nested-cmd"])
    assert result.exit_code == 1
    assert "Traceback (most recent call last):" in result.output
    assert "ValueError: Unexpected error in nested command" in result.output

    # Test with debug - also shows stack trace
    result = runner.invoke(cli, ["--debug", "subgroup", "nested-cmd"])
    assert result.exit_code == 1
    assert "Traceback (most recent call last):" in result.output
    assert "ValueError: Unexpected error in nested command" in result.output


def test_error_boundary_missing_context() -> None:
    """Test error boundary behavior when Click context is missing.

    Unexpected exceptions should show full stack traces regardless of context.
    """

    @cli_error_boundary
    def standalone_func() -> None:
        raise ValueError("Error without context")

    # Call function directly without Click context
    with pytest.raises(SystemExit) as exc_info:
        standalone_func()

    assert exc_info.value.code == 1


def test_error_boundary_artifact_conflict_error() -> None:
    """Test ArtifactConflictError shows clean message without debug."""

    @click.command()
    @cli_error_boundary
    def cmd() -> None:
        raise ArtifactConflictError(Path("/tmp/test.txt"))

    runner = CliRunner()
    result = runner.invoke(cmd, [])

    assert result.exit_code == 1
    assert "Error: Artifact already exists: /tmp/test.txt" in result.output
    assert "Use --force to replace existing files" in result.output
    assert "Traceback" not in result.output


def test_error_boundary_dotagnent_base_exception() -> None:
    """Test that all DotAgentNonIdealStateException subclasses show clean messages."""

    class CustomNonIdealError(DotAgentNonIdealStateException):
        """Custom non-ideal state exception for testing."""

        pass

    @click.command()
    @cli_error_boundary
    def cmd() -> None:
        raise CustomNonIdealError("Custom non-ideal state occurred")

    runner = CliRunner()
    result = runner.invoke(cmd, [])

    assert result.exit_code == 1
    assert "Error: Custom non-ideal state occurred" in result.output
    assert "Traceback" not in result.output
    assert "--debug" not in result.output


def test_error_boundary_multiple_exception_types() -> None:
    """Test error boundary with various exception types in debug mode."""

    @click.group()
    @click.option("--debug", is_flag=True)
    @click.pass_context
    def cli(ctx: click.Context, debug: bool) -> None:
        ctx.ensure_object(dict)
        ctx.obj["debug"] = debug

    @cli.command("type-error-cmd")
    @cli_error_boundary
    @click.pass_context
    def type_error_cmd(ctx: click.Context) -> None:
        raise TypeError("Type error occurred")

    @cli.command("attribute-error-cmd")
    @cli_error_boundary
    @click.pass_context
    def attribute_error_cmd(ctx: click.Context) -> None:
        raise AttributeError("Attribute error occurred")

    @cli.command("name-error-cmd")
    @cli_error_boundary
    @click.pass_context
    def name_error_cmd(ctx: click.Context) -> None:
        raise NameError("Name error occurred")

    runner = CliRunner()

    # Test TypeError
    result = runner.invoke(cli, ["--debug", "type-error-cmd"])
    assert result.exit_code == 1
    assert "Traceback" in result.output
    assert "TypeError: Type error occurred" in result.output

    # Test AttributeError
    result = runner.invoke(cli, ["--debug", "attribute-error-cmd"])
    assert result.exit_code == 1
    assert "Traceback" in result.output
    assert "AttributeError: Attribute error occurred" in result.output

    # Test NameError
    result = runner.invoke(cli, ["--debug", "name-error-cmd"])
    assert result.exit_code == 1
    assert "Traceback" in result.output
    assert "NameError: Name error occurred" in result.output


def test_error_boundary_context_object_not_dict() -> None:
    """Test error boundary when context object exists but isn't a dict.

    Unexpected exceptions should always show full stack traces.
    """

    @click.group()
    @click.option("--debug", is_flag=True)
    @click.pass_context
    def cli(ctx: click.Context, debug: bool) -> None:
        # Intentionally set context object to non-dict
        ctx.obj = "not a dict"

    @cli.command()
    @cli_error_boundary
    def cmd() -> None:
        raise ValueError("Error with non-dict context")

    runner = CliRunner()
    result = runner.invoke(cli, ["--debug", "cmd"])

    # Unexpected exceptions always show stack traces
    assert result.exit_code == 1
    assert "Traceback (most recent call last):" in result.output
    assert "ValueError: Error with non-dict context" in result.output


def test_error_boundary_context_obj_missing_debug_key() -> None:
    """Test error boundary when context object exists but has no 'debug' key.

    Unexpected exceptions should always show full stack traces.
    """

    @click.group()
    @click.pass_context
    def cli(ctx: click.Context) -> None:
        ctx.ensure_object(dict)
        # Intentionally don't set debug key

    @cli.command()
    @cli_error_boundary
    def cmd() -> None:
        raise ValueError("Error with missing debug key")

    runner = CliRunner()
    result = runner.invoke(cli, ["cmd"])

    # Unexpected exceptions always show stack traces
    assert result.exit_code == 1
    assert "Traceback (most recent call last):" in result.output
    assert "ValueError: Error with missing debug key" in result.output
