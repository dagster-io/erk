"""Tests for erk objective close command."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.context import context_for_test
from erk_shared.context.types import RepoContext
from erk_shared.gateway.console.fake import FakeConsole
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo


def _create_issue(
    number: int,
    *,
    state: str,
    labels: list[str],
    title: str | None = None,
) -> IssueInfo:
    """Create a test issue with the given state and labels."""
    return IssueInfo(
        number=number,
        title=title or f"Test Issue #{number}",
        body="Test body",
        state=state,
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=labels,
        assignees=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        author="testuser",
    )


def _create_repo_context(tmp_path: Path) -> RepoContext:
    """Create a RepoContext for testing."""
    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    return RepoContext(
        root=tmp_path,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )


def test_close_objective_successfully(tmp_path: Path) -> None:
    """Test closing an objective issue with --force flag."""
    issue = _create_issue(42, state="OPEN", labels=["erk-objective"])
    issues_ops = FakeGitHubIssues(username="testuser", issues={42: issue})

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "close", "42", "--force"], obj=ctx)

    assert result.exit_code == 0
    assert "Closed objective #42" in result.output
    assert issues_ops.closed_issues == [42]


def test_close_objective_requires_confirmation(tmp_path: Path) -> None:
    """Test that closing without --force prompts for confirmation."""
    issue = _create_issue(42, state="OPEN", labels=["erk-objective"], title="My Objective")
    issues_ops = FakeGitHubIssues(username="testuser", issues={42: issue})

    # User confirms
    console = FakeConsole(
        is_interactive=True,
        is_stdout_tty=None,
        is_stderr_tty=None,
        confirm_responses=[True],
    )
    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
        console=console,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "close", "42"], obj=ctx)

    assert result.exit_code == 0
    assert "Closed objective #42" in result.output
    assert issues_ops.closed_issues == [42]


def test_close_objective_cancelled_when_user_declines(tmp_path: Path) -> None:
    """Test that declining confirmation cancels the close."""
    issue = _create_issue(42, state="OPEN", labels=["erk-objective"], title="My Objective")
    issues_ops = FakeGitHubIssues(username="testuser", issues={42: issue})

    # User declines
    console = FakeConsole(
        is_interactive=True,
        is_stdout_tty=None,
        is_stderr_tty=None,
        confirm_responses=[False],
    )
    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
        console=console,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "close", "42"], obj=ctx)

    assert result.exit_code == 0
    assert "Cancelled" in result.output
    assert issues_ops.closed_issues == []


def test_close_objective_error_when_not_objective(tmp_path: Path) -> None:
    """Test that closing fails if issue lacks erk-objective label."""
    # Issue without erk-objective label
    issue = _create_issue(42, state="OPEN", labels=["bug"])
    issues_ops = FakeGitHubIssues(username="testuser", issues={42: issue})

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "close", "42", "--force"], obj=ctx)

    assert result.exit_code == 1
    assert "is not an objective" in result.output
    assert "missing 'erk-objective' label" in result.output
    assert issues_ops.closed_issues == []


def test_close_objective_error_when_already_closed(tmp_path: Path) -> None:
    """Test that closing fails if issue is already closed."""
    issue = _create_issue(42, state="CLOSED", labels=["erk-objective"])
    issues_ops = FakeGitHubIssues(username="testuser", issues={42: issue})

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "close", "42", "--force"], obj=ctx)

    assert result.exit_code == 1
    assert "already closed" in result.output
    assert issues_ops.closed_issues == []


def test_close_objective_accepts_github_url(tmp_path: Path) -> None:
    """Test closing with a full GitHub URL."""
    issue = _create_issue(123, state="OPEN", labels=["erk-objective"])
    issues_ops = FakeGitHubIssues(username="testuser", issues={123: issue})

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["objective", "close", "https://github.com/owner/repo/issues/123", "--force"],
        obj=ctx,
    )

    assert result.exit_code == 0
    assert "Closed objective #123" in result.output
    assert issues_ops.closed_issues == [123]


def test_close_objective_accepts_p_prefix(tmp_path: Path) -> None:
    """Test closing with P-prefixed issue number."""
    issue = _create_issue(456, state="OPEN", labels=["erk-objective"])
    issues_ops = FakeGitHubIssues(username="testuser", issues={456: issue})

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "close", "P456", "--force"], obj=ctx)

    assert result.exit_code == 0
    assert "Closed objective #456" in result.output
    assert issues_ops.closed_issues == [456]


def test_close_objective_alias_c_works(tmp_path: Path) -> None:
    """Test that 'c' alias works for close command."""
    issue = _create_issue(42, state="OPEN", labels=["erk-objective"])
    issues_ops = FakeGitHubIssues(username="testuser", issues={42: issue})

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "c", "42", "--force"], obj=ctx)

    assert result.exit_code == 0
    assert "Closed objective #42" in result.output
    assert issues_ops.closed_issues == [42]


def test_close_objective_requires_issue_ref_argument() -> None:
    """Test that close requires ISSUE_REF argument."""
    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "close"])

    assert result.exit_code == 2
    assert "Missing argument" in result.output
