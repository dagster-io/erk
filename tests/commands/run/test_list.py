"""CLI tests for erk workflow run list command.

This file focuses on CLI-specific concerns for the list runs command:
- Command execution and exit codes
- Output formatting and display (status indicators, Rich table)
- PR-centric view with direct PR extraction and plan→PR fallback

The integration layer (list_workflow_runs) is tested in:
- tests/unit/fakes/test_fake_github.py - Fake infrastructure tests
- tests/integration/test_real_github.py - Real implementation tests

This file trusts that unit layer and only tests CLI integration.
"""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.run.list_cmd import list_runs
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import PullRequestInfo, WorkflowRun
from tests.fakes.context import create_test_context


def _make_git(tmp_path: Path) -> FakeGit:
    """Create a standard FakeGit for run list tests."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    return FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )


def _repo_root(tmp_path: Path) -> Path:
    return tmp_path / "repo"


def _make_issue(number: int, title: str) -> IssueInfo:
    """Create a standard IssueInfo for testing."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=title,
        body="",
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )


def test_list_runs_empty_state(tmp_path: Path) -> None:
    """Test list command displays message when no runs found."""
    git_ops = _make_git(tmp_path)
    github_ops = FakeGitHub(workflow_runs=[])
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=_repo_root(tmp_path))

    runner = CliRunner()
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    assert "No workflow runs found" in result.output


def test_list_runs_pr_address_format_shows_pr(tmp_path: Path) -> None:
    """PR-address runs with #NNN in display_title show the PR number."""
    git_ops = _make_git(tmp_path)
    workflow_runs = [
        WorkflowRun(
            run_id="1234567890",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="pr-address:#456:abc123",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    issues_ops = FakeGitHubIssues(issues={
        1: _make_issue(1, "Dummy issue for location"),
    })
    ctx = create_test_context(git=git_ops, github=github_ops, issues=issues_ops, cwd=_repo_root(tmp_path))

    runner = CliRunner()
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    assert "1234567890" in result.output
    # PR number extracted from display_title #NNN format
    assert "#456" in result.output


def test_list_runs_new_plan_implement_format_shows_pr(tmp_path: Path) -> None:
    """New plan-implement format with #pr_number shows the PR directly."""
    git_ops = _make_git(tmp_path)
    workflow_runs = [
        WorkflowRun(
            run_id="555666",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="142:#460:abc456",  # New format: plan_id:#pr_number:distinct_id
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    issues_ops = FakeGitHubIssues(issues={
        1: _make_issue(1, "Dummy issue for location"),
    })
    ctx = create_test_context(git=git_ops, github=github_ops, issues=issues_ops, cwd=_repo_root(tmp_path))

    runner = CliRunner()
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    assert "#460" in result.output
    assert "plan-implement" in result.output


def test_list_runs_old_plan_format_falls_back_to_plan_pr_linkage(tmp_path: Path) -> None:
    """Old plan-implement format (no #pr) falls back to plan→PR linkage."""
    git_ops = _make_git(tmp_path)
    workflow_runs = [
        WorkflowRun(
            run_id="111222",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="142:abc456",  # Old format: plan_id:distinct_id (no #pr)
        ),
    ]

    pr_info = PullRequestInfo(
        number=201,
        state="OPEN",
        url="https://github.com/owner/repo/pull/201",
        is_draft=False,
        title="Add user auth",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    github_ops = FakeGitHub(
        workflow_runs=workflow_runs,
        pr_plan_linkages={142: [pr_info]},
    )
    issues_ops = FakeGitHubIssues(issues={
        142: _make_issue(142, "Add user authentication"),
    })
    ctx = create_test_context(git=git_ops, github=github_ops, issues=issues_ops, cwd=_repo_root(tmp_path))

    runner = CliRunner()
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    # PR number from linkage should appear
    assert "#201" in result.output
    # PR title should appear
    assert "Add user auth" in result.output
    # Checks should show passing
    assert "✅" in result.output


def test_list_runs_no_pr_shows_dash(tmp_path: Path) -> None:
    """Runs with no extractable PR number show '-' for pr/title/chks."""
    git_ops = _make_git(tmp_path)
    workflow_runs = [
        WorkflowRun(
            run_id="999888",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="Some legacy title [abc123]",  # No plan or PR number
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    issues_ops = FakeGitHubIssues(issues={
        1: _make_issue(1, "Dummy issue for location"),
    })
    ctx = create_test_context(git=git_ops, github=github_ops, issues=issues_ops, cwd=_repo_root(tmp_path))

    runner = CliRunner()
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    # Run should still appear (no filtering)
    assert "999888" in result.output
    # Should NOT show "X"
    assert "X" not in result.output


def test_list_runs_all_workflow_types_shown(tmp_path: Path) -> None:
    """All workflow types are shown without needing --show-legacy."""
    git_ops = _make_git(tmp_path)
    workflow_runs = [
        WorkflowRun(
            run_id="111111",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="142:#460:abc456",  # plan-implement with PR
        ),
        WorkflowRun(
            run_id="222222",
            status="completed",
            conclusion="success",
            branch="feat-2",
            head_sha="def456",
            display_title="pr-address:#460:def456",  # pr-address
        ),
        WorkflowRun(
            run_id="333333",
            status="completed",
            conclusion="success",
            branch="feat-3",
            head_sha="ghi789",
            display_title="one-shot:#461:ghi789",  # one-shot
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    issues_ops = FakeGitHubIssues(issues={
        1: _make_issue(1, "Dummy issue for location"),
    })
    ctx = create_test_context(git=git_ops, github=github_ops, issues=issues_ops, cwd=_repo_root(tmp_path))

    runner = CliRunner()
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    assert "111111" in result.output
    assert "222222" in result.output
    assert "333333" in result.output
    assert "#460" in result.output
    assert "#461" in result.output


def test_list_runs_multiple_statuses(tmp_path: Path) -> None:
    """Test list command displays multiple runs with different statuses."""
    git_ops = _make_git(tmp_path)
    now = datetime.now(UTC)
    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="142:#201:abc",
        ),
        WorkflowRun(
            run_id="999888",
            status="completed",
            conclusion="failure",
            branch="feat-2",
            head_sha="def456",
            display_title="143:#202:def",
        ),
        WorkflowRun(
            run_id="789",
            status="in_progress",
            conclusion=None,
            branch="feat-3",
            head_sha="ghi789",
            display_title="144:#203:ghi",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    issues_ops = FakeGitHubIssues(issues={
        1: _make_issue(1, "Dummy"),
    })
    ctx = create_test_context(git=git_ops, github=github_ops, issues=issues_ops, cwd=_repo_root(tmp_path))

    runner = CliRunner()
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    assert "123" in result.output
    assert "999888" in result.output
    assert "789" in result.output
    assert "#201" in result.output
    assert "#202" in result.output
    assert "#203" in result.output


def test_list_runs_truncates_long_titles(tmp_path: Path) -> None:
    """Test list command truncates PR titles longer than 50 characters."""
    git_ops = _make_git(tmp_path)
    long_title = (
        "This is a very long title that exceeds fifty characters "
        "and should be truncated with ellipsis"
    )
    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="142:abc",  # Old format, will use plan→PR linkage
        ),
    ]

    pr_info = PullRequestInfo(
        number=201,
        state="OPEN",
        url="https://github.com/owner/repo/pull/201",
        is_draft=False,
        title=long_title,
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    github_ops = FakeGitHub(
        workflow_runs=workflow_runs,
        pr_plan_linkages={142: [pr_info]},
    )
    issues_ops = FakeGitHubIssues(issues={
        142: _make_issue(142, "Plan title"),
    })
    ctx = create_test_context(git=git_ops, github=github_ops, issues=issues_ops, cwd=_repo_root(tmp_path))

    runner = CliRunner()
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    # Full title should NOT appear
    assert long_title not in result.output
    # Truncated version should appear with ellipsis
    assert "..." in result.output
    assert "This is a very long" in result.output


def test_list_runs_displays_submission_time(tmp_path: Path) -> None:
    """Test list command displays submission time in local timezone."""
    git_ops = _make_git(tmp_path)
    timestamp = datetime(2024, 11, 26, 14, 30, 45, tzinfo=UTC)
    workflow_runs = [
        WorkflowRun(
            run_id="1234567890",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="pr-address:#456:abc456",
            created_at=timestamp,
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    issues_ops = FakeGitHubIssues(issues={
        1: _make_issue(1, "Dummy"),
    })
    ctx = create_test_context(git=git_ops, github=github_ops, issues=issues_ops, cwd=_repo_root(tmp_path))

    runner = CliRunner()
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    assert "11-26" in result.output or "11-25" in result.output or "11-27" in result.output
    assert "submitted" in result.output


def test_list_runs_handles_missing_timestamp(tmp_path: Path) -> None:
    """Test list command handles missing created_at gracefully."""
    git_ops = _make_git(tmp_path)
    workflow_runs = [
        WorkflowRun(
            run_id="1234567890",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="pr-address:#456:abc456",
            created_at=None,
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    issues_ops = FakeGitHubIssues(issues={
        1: _make_issue(1, "Dummy"),
    })
    ctx = create_test_context(git=git_ops, github=github_ops, issues=issues_ops, cwd=_repo_root(tmp_path))

    runner = CliRunner()
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    assert "submitted" in result.output


def test_list_runs_shows_workflow_column(tmp_path: Path) -> None:
    """Test that runs display the workflow source column."""
    git_ops = _make_git(tmp_path)
    workflow_runs = [
        WorkflowRun(
            run_id="555666",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="142:#460:abc456",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    issues_ops = FakeGitHubIssues(issues={
        1: _make_issue(1, "Dummy"),
    })
    ctx = create_test_context(git=git_ops, github=github_ops, issues=issues_ops, cwd=_repo_root(tmp_path))

    runner = CliRunner()
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    assert "workflow" in result.output
    assert "plan-implement" in result.output
    assert "555666" in result.output
    assert "#460" in result.output


def test_list_runs_handles_queued_status(tmp_path: Path) -> None:
    """Test list command displays queued status correctly."""
    git_ops = _make_git(tmp_path)
    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="queued",
            conclusion=None,
            branch="feat-1",
            head_sha="abc123",
            display_title="pr-address:#456:abc",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    issues_ops = FakeGitHubIssues(issues={
        1: _make_issue(1, "Dummy"),
    })
    ctx = create_test_context(git=git_ops, github=github_ops, issues=issues_ops, cwd=_repo_root(tmp_path))

    runner = CliRunner()
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    assert "Queued" in result.output or "⧗" in result.output


def test_list_runs_handles_cancelled_status(tmp_path: Path) -> None:
    """Test list command displays cancelled status correctly."""
    git_ops = _make_git(tmp_path)
    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="cancelled",
            branch="feat-1",
            head_sha="abc123",
            display_title="pr-address:#456:abc",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    issues_ops = FakeGitHubIssues(issues={
        1: _make_issue(1, "Dummy"),
    })
    ctx = create_test_context(git=git_ops, github=github_ops, issues=issues_ops, cwd=_repo_root(tmp_path))

    runner = CliRunner()
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    assert "Cancelled" in result.output or "⛔" in result.output


def test_list_runs_pr_column_header(tmp_path: Path) -> None:
    """Table uses 'pr' column header instead of 'plan'."""
    git_ops = _make_git(tmp_path)
    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="pr-address:#456:abc",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    issues_ops = FakeGitHubIssues(issues={
        1: _make_issue(1, "Dummy"),
    })
    ctx = create_test_context(git=git_ops, github=github_ops, issues=issues_ops, cwd=_repo_root(tmp_path))

    runner = CliRunner()
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    # Should have "pr" column header, not "plan"
    assert "plan" not in result.output.lower().split("\n")[0] if result.output else True
    # The "pr" header appears in the table (Rich renders headers in bold)
    assert "pr" in result.output
