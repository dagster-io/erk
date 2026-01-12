"""Unit tests for learn status check prompts in land command."""

from pathlib import Path

import pytest

from erk.core.context import context_for_test
from erk_shared.github.issues import FakeGitHubIssues
from tests.test_utils.github_helpers import create_test_issue


def test_check_learn_status_and_prompt_skips_when_already_learned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that _check_learn_status_and_prompt shows positive feedback when plan has been
    learned from.
    """
    from erk.cli.commands import land_cmd
    from erk.cli.commands.land_cmd import _check_learn_status_and_prompt
    from erk_shared.sessions.discovery import SessionsForPlan

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Mock find_sessions_for_plan to return sessions with learn_session_ids
    def mock_find_sessions(github_issues, repo_root_arg, plan_issue_number):
        return SessionsForPlan(
            planning_session_id="plan-session-1",
            implementation_session_ids=["impl-session-1"],
            learn_session_ids=["learn-session-1"],  # Already learned
            last_remote_impl_at=None,
        )

    monkeypatch.setattr(land_cmd, "find_sessions_for_plan", mock_find_sessions)

    ctx = context_for_test(cwd=repo_root)

    # Should return without any interaction (plan already learned from)
    _check_learn_status_and_prompt(ctx, repo_root=repo_root, plan_issue_number=123, force=False)

    # Verify positive feedback is shown
    captured = capsys.readouterr()
    assert "Learn completed for plan #123" in captured.err


def test_check_learn_status_and_prompt_skips_when_force(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that _check_learn_status_and_prompt does nothing when force=True."""
    from erk.cli.commands import land_cmd
    from erk.cli.commands.land_cmd import _check_learn_status_and_prompt

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Mock should not be called when force=True
    find_sessions_called = []

    def mock_find_sessions(github_issues, repo_root_arg, plan_issue_number):
        find_sessions_called.append(True)
        raise AssertionError("Should not be called when force=True")

    monkeypatch.setattr(land_cmd, "find_sessions_for_plan", mock_find_sessions)

    ctx = context_for_test(cwd=repo_root)

    # With force=True, should return immediately without calling find_sessions_for_plan
    _check_learn_status_and_prompt(ctx, repo_root=repo_root, plan_issue_number=123, force=True)

    # Verify find_sessions was not called
    assert len(find_sessions_called) == 0


def test_check_learn_status_and_prompt_warns_when_not_learned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that _check_learn_status_and_prompt shows warning when not learned.

    When user confirms to continue, the function should return normally.
    """
    from erk.cli.commands import land_cmd
    from erk.cli.commands.land_cmd import _check_learn_status_and_prompt
    from erk_shared.sessions.discovery import SessionsForPlan

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Mock find_sessions_for_plan to return sessions WITHOUT learn_session_ids
    def mock_find_sessions(github_issues, repo_root_arg, plan_issue_number):
        return SessionsForPlan(
            planning_session_id="plan-session-1",
            implementation_session_ids=["impl-session-1"],
            learn_session_ids=[],  # Not learned
            last_remote_impl_at=None,
        )

    monkeypatch.setattr(land_cmd, "find_sessions_for_plan", mock_find_sessions)

    # Create context with FakeConsole that confirms (True)
    from erk_shared.gateway.console.fake import FakeConsole

    fake_console = FakeConsole(
        is_interactive=True,
        is_stdout_tty=True,
        is_stderr_tty=True,
        confirm_responses=[True],
    )
    ctx = context_for_test(cwd=repo_root, console=fake_console)

    # Should show warning and continue
    _check_learn_status_and_prompt(ctx, repo_root=repo_root, plan_issue_number=123, force=False)

    # Check that warning was shown
    captured = capsys.readouterr()
    assert "Warning:" in captured.err
    assert "#123" in captured.err
    assert "not been learned from" in captured.err


def test_check_learn_status_and_prompt_cancels_when_user_declines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that _check_learn_status_and_prompt exits when user declines to continue."""
    from erk.cli.commands import land_cmd
    from erk.cli.commands.land_cmd import _check_learn_status_and_prompt
    from erk_shared.sessions.discovery import SessionsForPlan

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Mock find_sessions_for_plan to return sessions WITHOUT learn_session_ids
    def mock_find_sessions(github_issues, repo_root_arg, plan_issue_number):
        return SessionsForPlan(
            planning_session_id="plan-session-1",
            implementation_session_ids=["impl-session-1"],
            learn_session_ids=[],  # Not learned
            last_remote_impl_at=None,
        )

    monkeypatch.setattr(land_cmd, "find_sessions_for_plan", mock_find_sessions)

    # Create context with FakeConsole that declines (False)
    from erk_shared.gateway.console.fake import FakeConsole

    fake_console = FakeConsole(
        is_interactive=True,
        is_stdout_tty=True,
        is_stderr_tty=True,
        confirm_responses=[False],
    )
    ctx = context_for_test(cwd=repo_root, console=fake_console)

    # Should raise SystemExit(0) when user declines
    with pytest.raises(SystemExit) as exc_info:
        _check_learn_status_and_prompt(ctx, repo_root=repo_root, plan_issue_number=123, force=False)

    assert exc_info.value.code == 0


def test_check_learn_status_and_prompt_skips_for_learn_plans(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that _check_learn_status_and_prompt skips check for learn plans.

    Learn plans (issues with erk-learn label) should not warn about needing
    to be learned from, since they are themselves for extracting insights.
    """
    from erk.cli.commands import land_cmd
    from erk.cli.commands.land_cmd import _check_learn_status_and_prompt

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    issue_number = 123

    # Create a learn plan issue (has erk-learn label)
    learn_issue = create_test_issue(
        number=issue_number,
        title="Learn: Extract testing patterns",
        labels=["erk-plan", "erk-learn"],
    )

    fake_issues = FakeGitHubIssues(issues={issue_number: learn_issue})

    # Mock find_sessions_for_plan - should NOT be called for learn plans
    find_sessions_called = []

    def mock_find_sessions(github_issues, repo_root_arg, plan_issue_number):
        find_sessions_called.append(True)
        raise AssertionError("find_sessions_for_plan should not be called for learn plans")

    monkeypatch.setattr(land_cmd, "find_sessions_for_plan", mock_find_sessions)

    ctx = context_for_test(cwd=repo_root, issues=fake_issues)

    # Should return immediately without calling find_sessions_for_plan
    _check_learn_status_and_prompt(
        ctx, repo_root=repo_root, plan_issue_number=issue_number, force=False
    )

    # Verify find_sessions was not called (function returned early)
    assert len(find_sessions_called) == 0
