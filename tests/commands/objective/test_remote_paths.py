"""Tests for objective command remote paths (--repo flag / NoRepoSentinel)."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.github.issues.types import IssueInfo
from tests.fakes.gateway.console import FakeConsole
from tests.fakes.gateway.remote_github import FakeRemoteGitHub
from tests.test_utils.test_context import context_for_test


def _make_fake_remote(
    *,
    issues: dict[int, IssueInfo] | None = None,
) -> FakeRemoteGitHub:
    """Create a FakeRemoteGitHub with sensible defaults."""
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


def _make_issue(
    number: int,
    *,
    title: str = "Test Objective",
    state: str = "OPEN",
    labels: list[str] | None = None,
    body: str = "Test objective body",
) -> IssueInfo:
    """Create a test IssueInfo with erk-objective label by default."""
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state=state,
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=labels if labels is not None else ["erk-objective"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        author="test-author",
    )


def _build_remote_context(fake_remote: FakeRemoteGitHub) -> context_for_test:
    """Build ErkContext configured for remote mode testing."""
    return context_for_test(
        repo=NoRepoSentinel(),
        remote_github=fake_remote,
    )


# --- objective view --repo ---


def test_view_remote_displays_objective() -> None:
    """Test objective view with --repo flag displays objective data."""
    issue = _make_issue(42, title="Remote Objective Title")
    fake_remote = _make_fake_remote(issues={42: issue})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "view", "42", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 0
    assert "Remote Objective Title" in result.output
    assert "#42" in result.output


def test_view_remote_not_found() -> None:
    """Test objective view --repo with non-existent issue."""
    fake_remote = _make_fake_remote(issues={})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "view", "999", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 1
    assert "#999 not found" in result.output


def test_view_remote_requires_identifier() -> None:
    """Test objective view --repo without identifier gives error."""
    fake_remote = _make_fake_remote()
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "view", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 1
    assert "No objective reference provided" in result.output


def test_view_remote_not_objective() -> None:
    """Test objective view --repo with issue lacking erk-objective label."""
    issue = _make_issue(42, labels=["bug"])
    fake_remote = _make_fake_remote(issues={42: issue})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "view", "42", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 1
    assert "not an objective" in result.output


# --- objective list --repo ---


def test_list_remote_shows_objectives() -> None:
    """Test objective list with --repo flag displays objectives."""
    issue1 = _make_issue(1, title="Objective One")
    issue2 = _make_issue(2, title="Objective Two")
    fake_remote = _make_fake_remote(issues={1: issue1, 2: issue2})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "list", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 0
    assert "#1" in result.output
    assert "#2" in result.output


def test_list_remote_empty() -> None:
    """Test objective list --repo with no objectives."""
    fake_remote = _make_fake_remote(issues={})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "list", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 0
    assert "No open objectives found" in result.output


# --- objective check --repo ---


def test_check_remote_validates_objective() -> None:
    """Test objective check with --repo flag runs validation."""
    issue = _make_issue(42)
    fake_remote = _make_fake_remote(issues={42: issue})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "check", "42", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 0
    assert "erk-objective label" in result.output


def test_check_remote_not_found() -> None:
    """Test objective check --repo with non-existent issue."""
    fake_remote = _make_fake_remote(issues={})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "check", "999", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 1
    assert "#999 not found" in result.output


def test_check_remote_json_output() -> None:
    """Test objective check --repo --json-output returns structured data."""
    issue = _make_issue(42)
    fake_remote = _make_fake_remote(issues={42: issue})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["objective", "check", "42", "--repo", "owner/repo", "--json-output"],
        obj=ctx,
    )

    assert result.exit_code == 0
    assert '"success": true' in result.output


# --- objective close --repo ---


def test_close_remote_closes_objective() -> None:
    """Test objective close with --repo flag closes the issue."""
    issue = _make_issue(42)
    fake_remote = _make_fake_remote(issues={42: issue})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["objective", "close", "42", "--repo", "owner/repo", "--force"], obj=ctx
    )

    assert result.exit_code == 0
    assert "Closed objective #42" in result.output
    assert len(fake_remote.closed_issues) == 1
    assert fake_remote.closed_issues[0].number == 42


def test_close_remote_not_found() -> None:
    """Test objective close --repo with non-existent issue."""
    fake_remote = _make_fake_remote(issues={})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["objective", "close", "999", "--repo", "owner/repo", "--force"], obj=ctx
    )

    assert result.exit_code == 1
    assert "#999 not found" in result.output


def test_close_remote_requires_confirmation() -> None:
    """Test objective close --repo prompts for confirmation without --force."""
    issue = _make_issue(42, title="My Remote Objective")
    fake_remote = _make_fake_remote(issues={42: issue})
    console = FakeConsole(
        is_interactive=True,
        is_stdout_tty=None,
        is_stderr_tty=None,
        confirm_responses=[True],
    )
    ctx = context_for_test(
        repo=NoRepoSentinel(),
        remote_github=fake_remote,
        console=console,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "close", "42", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 0
    assert "Closed objective #42" in result.output
    assert len(fake_remote.closed_issues) == 1


# --- repo_resolution edge cases ---


def test_invalid_repo_format() -> None:
    """Test --repo with invalid format gives helpful error."""
    fake_remote = _make_fake_remote()
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "view", "42", "--repo", "invalid"], obj=ctx)

    assert result.exit_code != 0
    assert "Invalid --repo format" in result.output
