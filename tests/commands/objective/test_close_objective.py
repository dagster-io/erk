"""Tests for erk objective close command."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.context.types import RepoContext
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import GitHubRepoId
from tests.fakes.gateway.console import FakeConsole
from tests.fakes.gateway.remote_github import FakeRemoteGitHub
from tests.test_utils.test_context import context_for_test


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


def _make_remote(issues: dict[int, IssueInfo]) -> FakeRemoteGitHub:
    """Create a FakeRemoteGitHub from an issue dict."""
    return FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=issues,
        issue_comments=None,
        pr_references=None,
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
        github=GitHubRepoId(owner="owner", repo="repo"),
    )


def test_close_objective_successfully(tmp_path: Path) -> None:
    """Test closing an objective issue with --force flag."""
    issue = _create_issue(42, state="OPEN", labels=["erk-objective"])
    fake_remote = _make_remote({42: issue})

    ctx = context_for_test(
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
        remote_github=fake_remote,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "close", "42", "--force"], obj=ctx)

    assert result.exit_code == 0
    assert "Closed objective #42" in result.output
    assert len(fake_remote.closed_issues) == 1
    assert fake_remote.closed_issues[0].number == 42


def test_close_objective_requires_confirmation(tmp_path: Path) -> None:
    """Test that closing without --force prompts for confirmation."""
    issue = _create_issue(42, state="OPEN", labels=["erk-objective"], title="My Objective")
    fake_remote = _make_remote({42: issue})

    # User confirms
    console = FakeConsole(
        is_interactive=True,
        is_stdout_tty=None,
        is_stderr_tty=None,
        confirm_responses=[True],
    )
    ctx = context_for_test(
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
        remote_github=fake_remote,
        console=console,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "close", "42"], obj=ctx)

    assert result.exit_code == 0
    assert "Closed objective #42" in result.output
    assert len(fake_remote.closed_issues) == 1
    assert fake_remote.closed_issues[0].number == 42


def test_close_objective_cancelled_when_user_declines(tmp_path: Path) -> None:
    """Test that declining confirmation cancels the close."""
    issue = _create_issue(42, state="OPEN", labels=["erk-objective"], title="My Objective")
    fake_remote = _make_remote({42: issue})

    # User declines
    console = FakeConsole(
        is_interactive=True,
        is_stdout_tty=None,
        is_stderr_tty=None,
        confirm_responses=[False],
    )
    ctx = context_for_test(
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
        remote_github=fake_remote,
        console=console,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "close", "42"], obj=ctx)

    assert result.exit_code == 0
    assert "Cancelled" in result.output
    assert fake_remote.closed_issues == []


def test_close_objective_error_when_not_objective(tmp_path: Path) -> None:
    """Test that closing fails if issue lacks erk-objective label."""
    # Issue without erk-objective label
    issue = _create_issue(42, state="OPEN", labels=["bug"])
    fake_remote = _make_remote({42: issue})

    ctx = context_for_test(
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
        remote_github=fake_remote,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "close", "42", "--force"], obj=ctx)

    assert result.exit_code == 1
    assert "is not an objective" in result.output
    assert "missing 'erk-objective' label" in result.output
    assert fake_remote.closed_issues == []


def test_close_objective_error_when_already_closed(tmp_path: Path) -> None:
    """Test that closing fails if issue is already closed."""
    issue = _create_issue(42, state="CLOSED", labels=["erk-objective"])
    fake_remote = _make_remote({42: issue})

    ctx = context_for_test(
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
        remote_github=fake_remote,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "close", "42", "--force"], obj=ctx)

    assert result.exit_code == 1
    assert "already closed" in result.output
    assert fake_remote.closed_issues == []


def test_close_objective_accepts_github_url(tmp_path: Path) -> None:
    """Test closing with a full GitHub URL."""
    issue = _create_issue(123, state="OPEN", labels=["erk-objective"])
    fake_remote = _make_remote({123: issue})

    ctx = context_for_test(
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
        remote_github=fake_remote,
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["objective", "close", "https://github.com/owner/repo/issues/123", "--force"],
        obj=ctx,
    )

    assert result.exit_code == 0
    assert "Closed objective #123" in result.output
    assert len(fake_remote.closed_issues) == 1
    assert fake_remote.closed_issues[0].number == 123


def test_close_objective_accepts_p_prefix(tmp_path: Path) -> None:
    """Test closing with P-prefixed issue number."""
    issue = _create_issue(456, state="OPEN", labels=["erk-objective"])
    fake_remote = _make_remote({456: issue})

    ctx = context_for_test(
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
        remote_github=fake_remote,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "close", "P456", "--force"], obj=ctx)

    assert result.exit_code == 0
    assert "Closed objective #456" in result.output
    assert len(fake_remote.closed_issues) == 1
    assert fake_remote.closed_issues[0].number == 456


def test_close_objective_alias_c_works(tmp_path: Path) -> None:
    """Test that 'c' alias works for close command."""
    issue = _create_issue(42, state="OPEN", labels=["erk-objective"])
    fake_remote = _make_remote({42: issue})

    ctx = context_for_test(
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
        remote_github=fake_remote,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "c", "42", "--force"], obj=ctx)

    assert result.exit_code == 0
    assert "Closed objective #42" in result.output
    assert len(fake_remote.closed_issues) == 1
    assert fake_remote.closed_issues[0].number == 42


def test_close_objective_requires_issue_ref_argument() -> None:
    """Test that close requires ISSUE_REF argument."""
    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "close"])

    assert result.exit_code == 2
    assert "Missing argument" in result.output
