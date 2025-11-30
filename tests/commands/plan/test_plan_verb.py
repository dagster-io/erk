"""Tests for plan command verb behavior (invoke_without_command).

Tests for:
- erk plan (no args) triggers remote planning
- erk plan --local triggers local planning
- erk plan "description" passes description
- Subcommands still work (list, get, etc.)
"""

from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.cli import cli
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


class TestPlanVerbBehavior:
    """Tests for plan command verb behavior."""

    def test_plan_without_args_triggers_remote_planning(self) -> None:
        """erk plan (no args) calls remote planning function."""
        runner = CliRunner()
        with erk_inmem_env(runner) as env:
            ctx = build_workspace_test_context(env)

            # Mock the remote planning function and os.execvp to prevent actual execution
            with (
                patch(
                    "erk.cli.commands.plan.get_or_create_codespace",
                    return_value="cs-test123",
                ),
                patch("os.execvp") as mock_execvp,
            ):
                runner.invoke(cli, ["plan"], obj=ctx)

                # Since os.execvp replaces the process, we check it was called
                mock_execvp.assert_called_once()
                call_args = mock_execvp.call_args
                assert call_args[0][0] == "gh"  # First arg is command name
                ssh_cmd = call_args[0][1]  # Second arg is full command list
                assert "codespace" in ssh_cmd
                assert "ssh" in ssh_cmd
                assert "claude" in ssh_cmd
                assert "/erk:craft-plan" in ssh_cmd

    def test_plan_with_description_passes_description_to_claude(self) -> None:
        """erk plan -m "description" includes description in Claude command."""
        runner = CliRunner()
        with erk_inmem_env(runner) as env:
            ctx = build_workspace_test_context(env)

            with (
                patch(
                    "erk.cli.commands.plan.get_or_create_codespace",
                    return_value="cs-test123",
                ),
                patch("os.execvp") as mock_execvp,
            ):
                runner.invoke(cli, ["plan", "-m", "add user authentication"], obj=ctx)

                mock_execvp.assert_called_once()
                ssh_cmd = mock_execvp.call_args[0][1]
                # Check that description is included
                assert any("add user authentication" in str(arg) for arg in ssh_cmd)

    def test_plan_local_triggers_local_planning(self) -> None:
        """erk plan --local calls local planning function with Claude."""
        runner = CliRunner()
        with erk_inmem_env(runner) as env:
            ctx = build_workspace_test_context(env)

            with (
                patch("shutil.which", return_value="/usr/bin/claude"),
                patch("os.execvp") as mock_execvp,
            ):
                runner.invoke(cli, ["plan", "--local"], obj=ctx)

                mock_execvp.assert_called_once()
                call_args = mock_execvp.call_args
                assert call_args[0][0] == "claude"
                cmd = call_args[0][1]
                assert "claude" in cmd
                assert "--permission-mode" in cmd
                assert "acceptEdits" in cmd
                assert "/erk:craft-plan" in cmd

    def test_plan_local_with_description(self) -> None:
        """erk plan --local -m "description" includes description."""
        runner = CliRunner()
        with erk_inmem_env(runner) as env:
            ctx = build_workspace_test_context(env)

            with (
                patch("shutil.which", return_value="/usr/bin/claude"),
                patch("os.execvp") as mock_execvp,
            ):
                runner.invoke(cli, ["plan", "--local", "-m", "add dark mode"], obj=ctx)

                mock_execvp.assert_called_once()
                cmd = mock_execvp.call_args[0][1]
                # Check description is included in the slash command
                assert any("add dark mode" in str(arg) for arg in cmd)

    def test_plan_local_fails_without_claude_cli(self) -> None:
        """erk plan --local errors if Claude CLI not found."""
        runner = CliRunner()
        with erk_inmem_env(runner) as env:
            ctx = build_workspace_test_context(env)

            with patch("shutil.which", return_value=None):
                result = runner.invoke(cli, ["plan", "--local"], obj=ctx)

                assert result.exit_code == 1
                assert "Claude CLI not found" in result.output


class TestPlanSubcommandsStillWork:
    """Tests that plan subcommands (noun usage) still work correctly."""

    def test_plan_list_subcommand_works(self) -> None:
        """erk plan list still invokes list command correctly."""
        runner = CliRunner()
        with erk_inmem_env(runner) as env:
            ctx = build_workspace_test_context(env)

            # list command will try to query GitHub, but with empty results
            result = runner.invoke(cli, ["plan", "list"], obj=ctx)

            # Should invoke the list command, not planning mode
            # Exit code depends on implementation details
            # The key is that it doesn't try to call remote planning
            assert "Looking for existing Codespace" not in result.output
            assert "Starting local planning" not in result.output

    def test_plan_help_shows_options_and_subcommands(self) -> None:
        """erk plan --help shows both verb options and subcommands."""
        runner = CliRunner()

        result = runner.invoke(cli, ["plan", "--help"])

        assert result.exit_code == 0
        # Check verb options are shown
        assert "--local" in result.output
        # Check subcommands are shown
        assert "list" in result.output
        assert "get" in result.output
        assert "create" in result.output
        assert "check" in result.output


class TestPlanRemotePlanningErrors:
    """Tests for error handling in remote planning."""

    def test_plan_handles_codespace_error(self) -> None:
        """erk plan shows error when codespace creation fails."""
        runner = CliRunner()
        with erk_inmem_env(runner) as env:
            ctx = build_workspace_test_context(env)

            from erk.core.codespace import CodespaceError

            with patch(
                "erk.cli.commands.plan.get_or_create_codespace",
                side_effect=CodespaceError("Codespace creation failed"),
            ):
                result = runner.invoke(cli, ["plan"], obj=ctx)

                assert result.exit_code != 0
