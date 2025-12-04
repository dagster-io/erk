"""Tests for CLI schema support (kit_json_command decorator)."""

import json
from dataclasses import dataclass

import click
from click.testing import CliRunner

from dot_agent_kit.cli.schema import build_epilog, kit_json_command


@dataclass
class SuccessResult:
    """Test success result."""

    success: bool
    message: str


@dataclass
class ErrorResult:
    """Test error result."""

    success: bool
    error: str


class TestBuildEpilog:
    """Tests for build_epilog function."""

    def test_build_epilog_single_type(self) -> None:
        """Test epilog generation for single result type."""
        epilog = build_epilog(SuccessResult)

        assert "SuccessResult:" in epilog
        assert "success:" in epilog
        assert "message:" in epilog

    def test_build_epilog_multiple_types(self) -> None:
        """Test epilog generation for multiple result types."""
        epilog = build_epilog(SuccessResult, ErrorResult)

        assert "SuccessResult:" in epilog
        assert "ErrorResult:" in epilog
        assert "message:" in epilog
        assert "error:" in epilog

    def test_build_epilog_empty(self) -> None:
        """Test epilog generation with no types."""
        epilog = build_epilog()
        assert epilog == ""


class TestKitJsonCommand:
    """Tests for kit_json_command decorator."""

    def test_success_result_with_exit_on_error_true(self) -> None:
        """Test command returns success result and exits 0."""

        @kit_json_command(
            name="test-cmd",
            results=[SuccessResult, ErrorResult],
            error_type=ErrorResult,
            exit_on_error=True,
        )
        def test_command(ctx: click.Context, value: str) -> SuccessResult | ErrorResult:
            return SuccessResult(success=True, message=f"Got {value}")

        # Add argument decorator
        test_command = click.argument("value")(test_command)

        runner = CliRunner()
        result = runner.invoke(test_command, ["hello"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["message"] == "Got hello"

    def test_error_result_with_exit_on_error_true(self) -> None:
        """Test command returns error result and exits 1 when exit_on_error=True."""

        @kit_json_command(
            name="test-cmd",
            results=[SuccessResult, ErrorResult],
            error_type=ErrorResult,
            exit_on_error=True,
        )
        def test_command(ctx: click.Context, fail: bool) -> SuccessResult | ErrorResult:
            if fail:
                return ErrorResult(success=False, error="Failed!")
            return SuccessResult(success=True, message="OK")

        # Add option decorator
        test_command = click.option("--fail", is_flag=True)(test_command)

        runner = CliRunner()
        result = runner.invoke(test_command, ["--fail"])

        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["success"] is False
        assert output["error"] == "Failed!"

    def test_error_result_with_exit_on_error_false(self) -> None:
        """Test command returns error result but exits 0 when exit_on_error=False."""

        @kit_json_command(
            name="test-cmd",
            results=[SuccessResult, ErrorResult],
            error_type=ErrorResult,
            exit_on_error=False,  # Graceful degradation
        )
        def test_command(ctx: click.Context, fail: bool) -> SuccessResult | ErrorResult:
            if fail:
                return ErrorResult(success=False, error="Failed!")
            return SuccessResult(success=True, message="OK")

        # Add option decorator
        test_command = click.option("--fail", is_flag=True)(test_command)

        runner = CliRunner()
        result = runner.invoke(test_command, ["--fail"])

        # Should exit 0 even though it's an error
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is False
        assert output["error"] == "Failed!"

    def test_context_is_passed(self) -> None:
        """Test that Click context is passed to command function."""

        @kit_json_command(
            name="test-cmd",
            results=[SuccessResult],
        )
        def test_command(ctx: click.Context) -> SuccessResult:
            # Verify we received a Click context
            assert ctx is not None
            assert isinstance(ctx, click.Context)
            return SuccessResult(success=True, message="Context received")

        runner = CliRunner()
        result = runner.invoke(test_command, [])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["message"] == "Context received"

    def test_context_obj_accessible(self) -> None:
        """Test that context.obj is accessible from command function."""

        @click.group()
        @click.pass_context
        def cli(ctx: click.Context) -> None:
            ctx.obj = {"test_value": "from_parent"}

        @kit_json_command(
            name="test-cmd",
            results=[SuccessResult],
        )
        def test_command(ctx: click.Context) -> SuccessResult:
            # Access context.obj set by parent
            value = ctx.obj.get("test_value", "not_found")
            return SuccessResult(success=True, message=value)

        cli.add_command(test_command)

        runner = CliRunner()
        result = runner.invoke(cli, ["test-cmd"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["message"] == "from_parent"

    def test_help_includes_schema(self) -> None:
        """Test that --help output includes result schema documentation."""

        @kit_json_command(
            name="test-cmd",
            results=[SuccessResult, ErrorResult],
        )
        def test_command(ctx: click.Context) -> SuccessResult:
            return SuccessResult(success=True, message="OK")

        runner = CliRunner()
        result = runner.invoke(test_command, ["--help"])

        assert result.exit_code == 0
        assert "SuccessResult:" in result.output
        assert "ErrorResult:" in result.output
        assert "success:" in result.output
        assert "message:" in result.output
        assert "error:" in result.output

    def test_command_with_multiple_arguments(self) -> None:
        """Test command with multiple Click arguments and options."""

        @kit_json_command(
            name="test-cmd",
            results=[SuccessResult],
        )
        def test_command(ctx: click.Context, name: str, value: int, flag: bool) -> SuccessResult:
            return SuccessResult(success=True, message=f"name={name}, value={value}, flag={flag}")

        # Add decorators in reverse order (Click requires this)
        test_command = click.option("--flag", is_flag=True)(test_command)
        test_command = click.option("--value", type=int, default=42)(test_command)
        test_command = click.argument("name")(test_command)

        runner = CliRunner()
        result = runner.invoke(test_command, ["test", "--value", "99", "--flag"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["message"] == "name=test, value=99, flag=True"

    def test_non_dataclass_result(self) -> None:
        """Test command returning non-dataclass JSON (dict)."""

        @kit_json_command(
            name="test-cmd",
            results=[],  # No schema for plain dict
        )
        def test_command(ctx: click.Context) -> dict[str, str]:
            return {"key": "value", "status": "ok"}

        runner = CliRunner()
        result = runner.invoke(test_command, [])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["key"] == "value"
        assert output["status"] == "ok"

    def test_command_without_error_type(self) -> None:
        """Test command without error_type specified."""

        @kit_json_command(
            name="test-cmd",
            results=[SuccessResult],
            # No error_type specified
        )
        def test_command(ctx: click.Context) -> SuccessResult:
            return SuccessResult(success=True, message="No error type")

        runner = CliRunner()
        result = runner.invoke(test_command, [])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["message"] == "No error type"

    def test_cli_kwargs_passed_through(self) -> None:
        """Test that additional Click kwargs are passed through."""

        @kit_json_command(
            name="test-cmd",
            results=[SuccessResult],
            help="Custom help text",
            short_help="Short help",
        )
        def test_command(ctx: click.Context) -> SuccessResult:
            return SuccessResult(success=True, message="OK")

        runner = CliRunner()
        result = runner.invoke(test_command, ["--help"])

        assert result.exit_code == 0
        assert "Custom help text" in result.output
