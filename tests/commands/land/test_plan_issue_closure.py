"""Tests for plan issue closure display in erk land command.

Tests the check_and_display_plan_issue_closure helper that shows:
- Confirmation when plan issue is closed after landing
- Warning when plan issue is unexpectedly still open
- Warning when PR is missing closing reference
- No output when branch has no plan issue prefix
"""

from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from erk.cli.commands.objective_helpers import check_and_display_plan_issue_closure
from erk.core.context import context_for_test
from erk_shared.context.types import LoadedConfig
from erk_shared.gateway.console.fake import FakeConsole
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.github.issues.abc import GitHubIssues
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo


def _create_issue(number: int, state: str) -> IssueInfo:
    """Create a test issue with the given state."""
    return IssueInfo(
        number=number,
        title=f"P{number}: Test Plan",
        body="Test body",
        state=state,
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        author="testuser",
    )


class StatefulFakeGitHubIssues(GitHubIssues):
    """Fake GitHubIssues that can change issue state between get_issue calls.

    Used to test retry logic - the issue starts OPEN and closes after N calls.
    """

    def __init__(
        self,
        *,
        issues: dict[int, IssueInfo],
        close_after_calls: int | None,
    ) -> None:
        """Create StatefulFakeGitHubIssues.

        Args:
            issues: Initial issue state
            close_after_calls: If set, close all issues after this many get_issue calls
        """
        self._issues = issues
        self._close_after_calls = close_after_calls
        self._get_issue_call_count = 0

    @property
    def get_issue_call_count(self) -> int:
        """Number of times get_issue was called."""
        return self._get_issue_call_count

    def get_issue(self, repo_root: Path, number: int) -> IssueInfo:
        """Get issue, potentially changing state based on call count."""
        self._get_issue_call_count += 1

        if number not in self._issues:
            msg = f"Issue #{number} not found"
            raise RuntimeError(msg)

        # Close issue after N calls if configured
        if (
            self._close_after_calls is not None
            and self._get_issue_call_count >= self._close_after_calls
        ):
            old_issue = self._issues[number]
            self._issues[number] = IssueInfo(
                number=old_issue.number,
                title=old_issue.title,
                body=old_issue.body,
                state="CLOSED",
                url=old_issue.url,
                labels=old_issue.labels,
                assignees=old_issue.assignees,
                created_at=old_issue.created_at,
                updated_at=old_issue.updated_at,
                author=old_issue.author,
            )

        return self._issues[number]

    # Stub out other required methods (not used by check_and_display_plan_issue_closure)
    def create_issue(self, *, repo_root: Path, title: str, body: str, labels: list[str]):
        raise NotImplementedError

    def add_comment(self, repo_root: Path, number: int, body: str) -> int:
        raise NotImplementedError

    def update_issue_body(self, repo_root: Path, number: int, body: str) -> None:
        raise NotImplementedError

    def list_issues(
        self,
        *,
        repo_root: Path,
        labels: list[str] | None = None,
        state: str | None = None,
        limit: int | None = None,
    ) -> list[IssueInfo]:
        raise NotImplementedError

    def get_issue_comments(self, repo_root: Path, number: int) -> list[str]:
        raise NotImplementedError

    def get_comment_by_id(self, repo_root: Path, comment_id: int) -> str:
        raise NotImplementedError

    def get_issue_comments_with_urls(self, repo_root: Path, number: int):
        raise NotImplementedError

    def ensure_label_exists(
        self, *, repo_root: Path, label: str, description: str, color: str
    ) -> None:
        raise NotImplementedError

    def label_exists(self, repo_root: Path, label: str) -> bool:
        raise NotImplementedError

    def ensure_label_on_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
        raise NotImplementedError

    def remove_label_from_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
        raise NotImplementedError

    def close_issue(self, repo_root: Path, number: int) -> None:
        raise NotImplementedError

    def get_current_username(self) -> str | None:
        return "testuser"

    def get_prs_referencing_issue(self, repo_root: Path, issue_number: int):
        raise NotImplementedError

    def add_reaction_to_comment(self, repo_root: Path, comment_id: int, reaction: str) -> None:
        raise NotImplementedError

    def update_comment(self, repo_root: Path, comment_id: int, body: str) -> None:
        raise NotImplementedError


def test_displays_closed_confirmation_when_issue_closed(tmp_path: Path) -> None:
    """Test that closed plan issue shows green checkmark confirmation."""
    issue = _create_issue(42, "CLOSED")
    issues_ops = FakeGitHubIssues(username="testuser", issues={42: issue})
    fake_time = FakeTime()

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        time=fake_time,
    )

    # Capture stderr output (user_output goes to stderr)
    captured = StringIO()
    with patch("sys.stderr", captured):
        result = check_and_display_plan_issue_closure(
            ctx,
            tmp_path,
            "P42-test-feature",
            pr_body="Closes #42",
        )

    assert result == 42
    output = captured.getvalue()
    assert "Closed plan issue #42" in output
    # No retries needed when already closed
    assert fake_time.sleep_calls == []


def test_with_closing_ref_retries_and_succeeds(tmp_path: Path) -> None:
    """Test that PR with closing ref retries until issue closes."""
    issue = _create_issue(42, "OPEN")
    # Issue closes after 2 get_issue calls (initial + 1 retry)
    issues_ops = StatefulFakeGitHubIssues(
        issues={42: issue},
        close_after_calls=2,
    )
    fake_time = FakeTime()

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        time=fake_time,
    )

    captured = StringIO()
    with patch("sys.stderr", captured):
        result = check_and_display_plan_issue_closure(
            ctx,
            tmp_path,
            "P42-test-feature",
            pr_body="Closes #42",
        )

    assert result == 42
    output = captured.getvalue()
    assert "Closed plan issue #42" in output
    # Should have retried once (slept once)
    assert fake_time.sleep_calls == [1.0]
    # Initial call + 1 retry
    assert issues_ops.get_issue_call_count == 2


def test_with_closing_ref_warns_after_max_retries(tmp_path: Path) -> None:
    """Test that PR with closing ref shows warning if issue never closes."""
    issue = _create_issue(42, "OPEN")
    # Issue never closes
    issues_ops = StatefulFakeGitHubIssues(
        issues={42: issue},
        close_after_calls=None,
    )
    fake_time = FakeTime()

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        time=fake_time,
    )

    captured = StringIO()
    with patch("sys.stderr", captured):
        result = check_and_display_plan_issue_closure(
            ctx,
            tmp_path,
            "P42-test-feature",
            pr_body="Closes #42",
        )

    assert result == 42
    output = captured.getvalue()
    assert "Plan issue #42 still open" in output
    assert "expected auto-close" in output
    # Should have retried 3 times (max retries)
    assert fake_time.sleep_calls == [1.0, 1.0, 1.0]
    # Initial call + 3 retries = 4 calls
    assert issues_ops.get_issue_call_count == 4


def test_without_closing_ref_warns_issue_wont_close(tmp_path: Path) -> None:
    """Test that PR missing closing ref shows specific warning."""
    issue = _create_issue(42, "OPEN")
    issues_ops = FakeGitHubIssues(username="testuser", issues={42: issue})
    fake_time = FakeTime()

    # User declines to close issue
    console = FakeConsole(
        is_interactive=True,
        is_stdout_tty=None,
        is_stderr_tty=None,
        confirm_responses=[False],
    )
    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        time=fake_time,
        console=console,
    )

    captured = StringIO()
    with patch("sys.stderr", captured):
        result = check_and_display_plan_issue_closure(
            ctx,
            tmp_path,
            "P42-test-feature",
            pr_body="Some PR body without closing reference",
        )

    assert result == 42
    output = captured.getvalue()
    assert "PR missing closing reference" in output
    assert "#42 won't auto-close" in output
    # No retries when closing ref is missing
    assert fake_time.sleep_calls == []
    # Issue should NOT have been closed (user declined)
    assert issues_ops.closed_issues == []


def test_without_closing_ref_succeeds_if_already_closed(tmp_path: Path) -> None:
    """Test that manually closed issue shows success even without closing ref."""
    issue = _create_issue(42, "CLOSED")
    issues_ops = FakeGitHubIssues(username="testuser", issues={42: issue})
    fake_time = FakeTime()

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        time=fake_time,
    )

    captured = StringIO()
    with patch("sys.stderr", captured):
        result = check_and_display_plan_issue_closure(
            ctx,
            tmp_path,
            "P42-test-feature",
            pr_body="Some PR body without closing reference",
        )

    assert result == 42
    output = captured.getvalue()
    assert "Closed plan issue #42" in output
    # No retries needed when already closed
    assert fake_time.sleep_calls == []


def test_cross_repo_closing_reference(tmp_path: Path) -> None:
    """Test that cross-repo closing reference (owner/repo#N) is detected."""
    issue = _create_issue(42, "CLOSED")
    issues_ops = FakeGitHubIssues(username="testuser", issues={42: issue})
    fake_time = FakeTime()
    # Configure plans_repo for cross-repo reference
    local_config = LoadedConfig.test(plans_repo="owner/plans-repo")

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        time=fake_time,
        local_config=local_config,
    )

    captured = StringIO()
    with patch("sys.stderr", captured):
        result = check_and_display_plan_issue_closure(
            ctx,
            tmp_path,
            "P42-test-feature",
            pr_body="Closes owner/plans-repo#42",
        )

    assert result == 42
    output = captured.getvalue()
    assert "Closed plan issue #42" in output


def test_cross_repo_missing_reference_warns(tmp_path: Path) -> None:
    """Test that missing cross-repo reference shows warning."""
    issue = _create_issue(42, "OPEN")
    issues_ops = FakeGitHubIssues(username="testuser", issues={42: issue})
    fake_time = FakeTime()
    # Configure plans_repo for cross-repo reference
    local_config = LoadedConfig.test(plans_repo="owner/plans-repo")

    # User declines to close issue
    console = FakeConsole(
        is_interactive=True,
        is_stdout_tty=None,
        is_stderr_tty=None,
        confirm_responses=[False],
    )
    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        time=fake_time,
        local_config=local_config,
        console=console,
    )

    captured = StringIO()
    with patch("sys.stderr", captured):
        result = check_and_display_plan_issue_closure(
            ctx,
            tmp_path,
            "P42-test-feature",
            # Wrong: same-repo reference when plans_repo is configured
            pr_body="Closes #42",
        )

    assert result == 42
    output = captured.getvalue()
    assert "PR missing closing reference" in output


def test_returns_none_for_non_plan_branch(tmp_path: Path) -> None:
    """Test that branches without P<num>- prefix return None with no output."""
    issues_ops = FakeGitHubIssues(username="testuser", issues={})
    fake_time = FakeTime()

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        time=fake_time,
    )

    captured = StringIO()
    with patch("sys.stderr", captured):
        result = check_and_display_plan_issue_closure(
            ctx,
            tmp_path,
            "feature-branch",
            pr_body="Some PR body",
        )

    assert result is None
    assert captured.getvalue() == ""


def test_returns_none_when_issue_not_found(tmp_path: Path) -> None:
    """Test that missing issue returns None with no output."""
    # No issues exist
    issues_ops = FakeGitHubIssues(username="testuser", issues={})
    fake_time = FakeTime()

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        time=fake_time,
    )

    captured = StringIO()
    with patch("sys.stderr", captured):
        result = check_and_display_plan_issue_closure(
            ctx,
            tmp_path,
            "P42-test-feature",
            pr_body="Closes #42",
        )

    assert result is None
    assert captured.getvalue() == ""


def test_handles_branch_with_complex_prefix(tmp_path: Path) -> None:
    """Test that complex branch names with P<num>- are handled correctly."""
    issue = _create_issue(1234, "CLOSED")
    issues_ops = FakeGitHubIssues(username="testuser", issues={1234: issue})
    fake_time = FakeTime()

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        time=fake_time,
    )

    captured = StringIO()
    with patch("sys.stderr", captured):
        result = check_and_display_plan_issue_closure(
            ctx,
            tmp_path,
            "P1234-add-feature-with-long-name-01-05-1430",
            pr_body="Closes #1234",
        )

    assert result == 1234
    output = captured.getvalue()
    assert "Closed plan issue #1234" in output


def test_without_closing_ref_offers_to_close_and_user_accepts(tmp_path: Path) -> None:
    """Test that user confirming closes the issue when PR missing closing ref."""
    issue = _create_issue(42, "OPEN")
    issues_ops = FakeGitHubIssues(username="testuser", issues={42: issue})
    fake_time = FakeTime()

    # User accepts to close issue
    console = FakeConsole(
        is_interactive=True,
        is_stdout_tty=None,
        is_stderr_tty=None,
        confirm_responses=[True],
    )
    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        time=fake_time,
        console=console,
    )

    captured = StringIO()
    with patch("sys.stderr", captured):
        result = check_and_display_plan_issue_closure(
            ctx,
            tmp_path,
            "P42-test-feature",
            pr_body="Some PR body without closing reference",
        )

    assert result == 42
    output = captured.getvalue()
    # Should show warning about missing closing reference
    assert "PR missing closing reference" in output
    assert "#42 won't auto-close" in output
    # Should show confirmation that issue was closed
    assert "Closed plan issue #42" in output
    # Issue should have been closed
    assert issues_ops.closed_issues == [42]


def test_without_closing_ref_offers_to_close_and_user_declines(tmp_path: Path) -> None:
    """Test that user declining leaves issue open when PR missing closing ref."""
    issue = _create_issue(42, "OPEN")
    issues_ops = FakeGitHubIssues(username="testuser", issues={42: issue})
    fake_time = FakeTime()

    # User declines to close issue
    console = FakeConsole(
        is_interactive=True,
        is_stdout_tty=None,
        is_stderr_tty=None,
        confirm_responses=[False],
    )
    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        time=fake_time,
        console=console,
    )

    captured = StringIO()
    with patch("sys.stderr", captured):
        result = check_and_display_plan_issue_closure(
            ctx,
            tmp_path,
            "P42-test-feature",
            pr_body="Some PR body without closing reference",
        )

    assert result == 42
    output = captured.getvalue()
    # Should show warning about missing closing reference
    assert "PR missing closing reference" in output
    assert "#42 won't auto-close" in output
    # Should NOT show confirmation message (user declined)
    assert "Closed plan issue #42" not in output
    # Issue should NOT have been closed
    assert issues_ops.closed_issues == []
