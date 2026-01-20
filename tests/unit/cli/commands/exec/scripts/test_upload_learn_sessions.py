"""Unit tests for upload_learn_sessions exec script.

Tests for the `erk exec upload-learn-sessions` command which uploads
preprocessed session files to a GitHub gist.
"""

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.upload_learn_sessions import (
    upload_learn_sessions,
)
from erk_shared.context.context import ErkContext


def test_upload_learn_sessions_requires_plan_issue() -> None:
    """Test that --plan-issue is required."""
    runner = CliRunner()
    ctx = ErkContext.for_test()

    result = runner.invoke(
        upload_learn_sessions,
        ["--session-id=test-session"],
        obj=ctx,
    )

    assert result.exit_code == 2
    assert "Missing option '--plan-issue'" in result.output


def test_upload_learn_sessions_requires_session_id() -> None:
    """Test that --session-id is required."""
    runner = CliRunner()
    ctx = ErkContext.for_test()

    result = runner.invoke(
        upload_learn_sessions,
        ["--plan-issue=123"],
        obj=ctx,
    )

    assert result.exit_code == 2
    assert "Missing option '--session-id'" in result.output


def test_upload_learn_sessions_command_registered() -> None:
    """Test that upload-learn-sessions command is registered in exec group."""
    from erk.cli.commands.exec.group import exec_group

    command_names = [cmd.name for cmd in exec_group.commands.values()]
    assert "upload-learn-sessions" in command_names
