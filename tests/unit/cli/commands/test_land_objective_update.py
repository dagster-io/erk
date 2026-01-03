"""Unit tests for objective update prompt in land command."""

from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from erk.cli.commands.land_cmd import _prompt_objective_update
from erk.core.context import context_for_test
from tests.fakes.claude_executor import FakeClaudeExecutor


def test_prompt_objective_update_force_skips_prompt() -> None:
    """Test that --force flag skips prompt and prints command for later."""
    executor = FakeClaudeExecutor()
    ctx = context_for_test(claude_executor=executor)

    captured_output = StringIO()
    with patch("erk.cli.commands.land_cmd.user_output") as mock_output:
        # Capture all calls to user_output
        mock_output.side_effect = lambda msg: captured_output.write(msg + "\n")

        _prompt_objective_update(
            ctx=ctx,
            repo_root=Path("/repo"),
            objective_number=42,
            pr_number=123,
            force=True,
        )

    output = captured_output.getvalue()

    # Should print objective info and command to run later
    assert "Linked to Objective #42" in output
    assert "/objective:update-landed-pr" in output

    # Should NOT have called claude executor (no prompt shown)
    assert len(executor.executed_commands) == 0


def test_prompt_objective_update_skip_option() -> None:
    """Test that user choosing option 1 skips update and shows command."""
    executor = FakeClaudeExecutor()
    ctx = context_for_test(claude_executor=executor)

    captured_output = StringIO()
    with (
        patch("erk.cli.commands.land_cmd.user_output") as mock_output,
        patch("click.prompt", return_value="1"),  # User chooses "1" to skip
    ):
        mock_output.side_effect = lambda msg: captured_output.write(msg + "\n")

        _prompt_objective_update(
            ctx=ctx,
            repo_root=Path("/repo"),
            objective_number=42,
            pr_number=123,
            force=False,
        )

    output = captured_output.getvalue()

    # Should show skip message with command
    assert "Skipped" in output
    assert "/objective:update-landed-pr" in output

    # Should NOT have called claude executor
    assert len(executor.executed_commands) == 0


def test_prompt_objective_update_run_now_option_success() -> None:
    """Test that user choosing option 2 runs Claude streaming and succeeds."""
    executor = FakeClaudeExecutor()  # Defaults to success
    ctx = context_for_test(claude_executor=executor)

    # Mock Console to prevent output pollution in tests
    mock_console = MagicMock()
    with (
        patch("erk.cli.commands.land_cmd.user_output"),
        patch("click.prompt", return_value="2"),  # User chooses "2" to run now
        patch("erk.cli.output.Console", return_value=mock_console),
    ):
        _prompt_objective_update(
            ctx=ctx,
            repo_root=Path("/repo"),
            objective_number=42,
            pr_number=123,
            force=False,
        )

    # Should have called claude executor streaming with correct command
    # Streaming API records: (command, path, dangerous, verbose, model)
    assert len(executor.executed_commands) == 1
    cmd, path, dangerous, verbose, model = executor.executed_commands[0]
    assert cmd == "/objective:update-landed-pr"
    assert path == Path("/repo")
    assert dangerous is True


def test_prompt_objective_update_run_now_option_failure() -> None:
    """Test that Claude streaming failure shows warning and manual command."""
    executor = FakeClaudeExecutor(command_should_fail=True)
    ctx = context_for_test(claude_executor=executor)

    captured_output = StringIO()
    # Mock Console to prevent output pollution in tests
    mock_console = MagicMock()
    with (
        patch("erk.cli.commands.land_cmd.user_output") as mock_output,
        patch("click.prompt", return_value="2"),  # User chooses "2" to run now
        patch("erk.cli.output.Console", return_value=mock_console),
    ):
        mock_output.side_effect = lambda msg: captured_output.write(msg + "\n")

        _prompt_objective_update(
            ctx=ctx,
            repo_root=Path("/repo"),
            objective_number=42,
            pr_number=123,
            force=False,
        )

    output = captured_output.getvalue()

    # Should show failure message with manual retry command
    assert "failed" in output.lower()
    assert "/objective:update-landed-pr" in output
    assert "manually" in output.lower()

    # Should have tried to call claude executor (streaming API)
    assert len(executor.executed_commands) == 1
