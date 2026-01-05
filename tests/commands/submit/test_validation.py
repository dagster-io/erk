"""Tests for submit command validation."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import ERK_PLAN_LABEL, submit_cmd
from erk.core.context import context_for_test
from erk.core.repo_discovery import RepoContext
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo
from tests.commands.submit.conftest import make_plan_body


def test_submit_missing_erk_plan_label(tmp_path: Path) -> None:
    """Test submit rejects issue without erk-plan label."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create issue WITHOUT erk-plan label
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Regular issue",
        body="Not a plan issue",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=["bug"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
    )
    fake_github = FakeGitHub()

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )
    ctx = context_for_test(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 1
    assert "does not have erk-plan label" in result.output
    assert "Cannot submit non-plan issues" in result.output

    # Verify workflow was NOT triggered
    assert len(fake_github.triggered_workflows) == 0


def test_submit_closed_issue(tmp_path: Path) -> None:
    """Test submit rejects closed issues."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create CLOSED issue with erk-plan label
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body=make_plan_body(),
        state="CLOSED",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
    )
    fake_github = FakeGitHub()

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )
    ctx = context_for_test(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 1
    assert "is CLOSED" in result.output
    assert "Cannot submit closed issues" in result.output

    # Verify workflow was NOT triggered
    assert len(fake_github.triggered_workflows) == 0


def test_submit_issue_not_found(tmp_path: Path) -> None:
    """Test submit handles missing issue gracefully."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Empty issues dict - issue 999 doesn't exist
    fake_github_issues = FakeGitHubIssues(issues={})
    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
    )
    fake_github = FakeGitHub()

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )
    ctx = context_for_test(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["999"], obj=ctx)

    # Should fail with RuntimeError from get_issue
    assert result.exit_code != 0
    assert "Issue #999 not found" in result.output


def test_submit_requires_gh_authentication(tmp_path: Path) -> None:
    """Test submit fails early if gh CLI is not authenticated (LBYL)."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create valid issue with erk-plan label
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body=make_plan_body(),
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    fake_git = FakeGit()
    # Configure FakeGitHub to simulate unauthenticated state
    fake_github = FakeGitHub(authenticated=False)

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )
    ctx = context_for_test(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    # Should fail early with authentication error (LBYL)
    assert result.exit_code == 1
    assert "Error: GitHub CLI (gh) is not authenticated" in result.output
    assert "gh auth login" in result.output

    # Verify workflow was NOT triggered (failure happened before workflow dispatch)
    assert len(fake_github.triggered_workflows) == 0
