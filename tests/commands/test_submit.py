"""Tests for erk submit command."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo
from erk_shared.naming import derive_branch_name_with_date
from erk_shared.plan_store.fake import FakePlanStore
from erk_shared.plan_store.types import Plan, PlanState

from erk.cli.commands.submit import ERK_PLAN_LABEL, _strip_plan_markers, submit_cmd
from erk.core.context import ErkContext
from erk.core.git.fake import FakeGit
from erk.core.github.fake import FakeGitHub
from erk.core.repo_discovery import RepoContext


def test_submit_creates_branch_and_draft_pr(tmp_path: Path) -> None:
    """Test submit creates local branch, pushes, creates draft PR, then triggers workflow."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create issue with erk-plan label, OPEN state
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body="# Plan\n\nImplementation details...",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    # Create plan for the issue
    plan = Plan(
        plan_identifier="123",
        title="Implement feature X",
        body="# Plan\n\nImplementation details...",
        state=PlanState.OPEN,
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
        metadata={},
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    fake_plan_store = FakePlanStore(plans={"123": plan})
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
    )
    ctx = ErkContext.for_test(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        plan_store=fake_plan_store,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "Issue submitted successfully!" in result.output
    assert "View workflow run:" in result.output

    # Expected branch name with date suffix
    expected_branch = derive_branch_name_with_date("Implement feature X")

    # Verify empty commit was created (no staged files, allow_empty=True)
    assert len(fake_git.commits) == 1
    cwd, message, staged_files, allow_empty = fake_git.commits[0]
    assert "Initialize implementation for issue #123" in message
    assert staged_files == []  # No files staged (empty commit)
    assert allow_empty is True

    # Verify branch was created and pushed
    assert len(fake_git.pushed_branches) == 1
    remote, branch, set_upstream = fake_git.pushed_branches[0]
    assert remote == "origin"
    assert branch == expected_branch
    assert branch.startswith("implement-feature-x-")
    assert set_upstream is True

    # Verify draft PR was created
    assert len(fake_github.created_prs) == 1
    branch_name, title, body, base, draft = fake_github.created_prs[0]
    assert branch_name == expected_branch
    assert branch_name.startswith("implement-feature-x-")
    assert title == "Implement feature X"
    assert draft is True
    assert "Closes #123" in body

    # Verify workflow was triggered
    assert len(fake_github.triggered_workflows) == 1
    workflow, inputs = fake_github.triggered_workflows[0]
    assert workflow == "dispatch-erk-queue-git.yml"
    assert inputs["issue_number"] == "123"

    # Verify local branch was cleaned up
    assert len(fake_git._deleted_branches) == 1
    assert expected_branch in fake_git._deleted_branches


def test_submit_skips_branch_creation_when_exists(tmp_path: Path) -> None:
    """Test submit skips branch/PR creation when branch already exists on remote."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body="# Plan\n\nImplementation details...",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    # Expected branch name with date suffix
    expected_branch = derive_branch_name_with_date("Implement feature X")

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
        # Simulate branch existing on remote with date suffix
        remote_branches={repo_root: [f"origin/{expected_branch}"]},
    )
    # Set up PR status for existing branch
    fake_github = FakeGitHub(pr_statuses={expected_branch: ("OPEN", 456, "Implement feature X")})

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = ErkContext.for_test(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "PR #456 already exists" in result.output
    assert "Skipping branch/PR creation" in result.output

    # Verify no branch/PR was created
    assert len(fake_git.pushed_branches) == 0
    assert len(fake_github.created_prs) == 0

    # Workflow should still be triggered
    assert len(fake_github.triggered_workflows) == 1


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
    )
    ctx = ErkContext.for_test(
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
        body="# Plan\n\nImplementation details...",
        state="CLOSED",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
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
    )
    ctx = ErkContext.for_test(
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
    )
    ctx = ErkContext.for_test(
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


def test_submit_displays_workflow_run_url(tmp_path: Path) -> None:
    """Test submit displays workflow run URL from trigger_workflow response."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create issue with erk-plan label, OPEN state
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Add workflow run URL to erk submit output",
        body="# Plan\n\nImplementation details...",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    # Create plan for the issue
    plan = Plan(
        plan_identifier="123",
        title="Add workflow run URL to erk submit output",
        body="# Plan\n\nImplementation details...",
        state=PlanState.OPEN,
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
        metadata={},
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    fake_plan_store = FakePlanStore(plans={"123": plan})
    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
    )
    # FakeGitHub.trigger_workflow() returns "1234567890" by default
    fake_github = FakeGitHub()

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = ErkContext.for_test(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        plan_store=fake_plan_store,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "Issue submitted successfully!" in result.output
    # Verify workflow run URL is displayed (uses run_id returned by trigger_workflow)
    expected_url = (
        "View workflow run: https://github.com/test-owner/test-repo/actions/runs/1234567890"
    )
    assert expected_url in result.output


def test_submit_requires_gh_authentication(tmp_path: Path) -> None:
    """Test submit fails early if gh CLI is not authenticated (LBYL)."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create valid issue with erk-plan label
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body="# Plan\n\nImplementation details...",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
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
    )
    ctx = ErkContext.for_test(
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


def test_strip_plan_markers() -> None:
    """Test _strip_plan_markers removes 'Plan:' prefix and '[erk-plan]' suffix from titles."""
    # Strip [erk-plan] suffix only
    assert _strip_plan_markers("Implement feature X [erk-plan]") == "Implement feature X"
    assert _strip_plan_markers("Implement feature X") == "Implement feature X"
    assert _strip_plan_markers(" [erk-plan]") == ""
    assert _strip_plan_markers("Planning [erk-plan] ahead") == "Planning [erk-plan] ahead"
    # Strip Plan: prefix only
    assert _strip_plan_markers("Plan: Implement feature X") == "Implement feature X"
    assert _strip_plan_markers("Plan: Already has prefix") == "Already has prefix"
    # Strip both Plan: prefix and [erk-plan] suffix
    assert _strip_plan_markers("Plan: Implement feature X [erk-plan]") == "Implement feature X"
    # No stripping needed
    assert _strip_plan_markers("Regular title") == "Regular title"


def test_submit_strips_plan_markers_from_pr_title(tmp_path: Path) -> None:
    """Test submit strips plan markers from issue title when creating PR."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)
    # Issue with "[erk-plan]" suffix (standard format for erk-plan issues)
    issue = IssueInfo(
        number=123,
        title="Implement feature X [erk-plan]",
        body="# Plan\n\nImplementation details...",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    plan = Plan(
        plan_identifier="123",
        title="Implement feature X [erk-plan]",
        body="# Plan\n\nImplementation details...",
        state=PlanState.OPEN,
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
        metadata={},
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    fake_plan_store = FakePlanStore(plans={"123": plan})
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
    )
    ctx = ErkContext.for_test(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        plan_store=fake_plan_store,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output

    # Verify PR was created with stripped title (no "[erk-plan]" suffix)
    assert len(fake_github.created_prs) == 1
    branch_name, title, body, base, draft = fake_github.created_prs[0]
    assert title == "Implement feature X"  # NOT "Implement feature X [erk-plan]"

    # Verify PR body was updated with checkout footer
    assert len(fake_github.updated_pr_bodies) == 1
    pr_number, updated_body = fake_github.updated_pr_bodies[0]
    assert pr_number == 999  # FakeGitHub returns 999 for created PRs
    assert "erk pr checkout 999" in updated_body
