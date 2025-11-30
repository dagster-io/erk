"""Tests for erk submit command."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo
from erk_shared.github.types import PullRequestInfo
from erk_shared.naming import derive_branch_name_with_date
from erk_shared.plan_store.fake import FakePlanStore
from erk_shared.plan_store.types import Plan, PlanState

from erk.cli.commands.submit import (
    ERK_PLAN_LABEL,
    ValidatedIssue,
    _close_orphaned_draft_prs,
    _strip_plan_markers,
    _validate_issue_for_submit,
    submit_cmd,
)
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
    assert "1 issue(s) submitted successfully!" in result.output
    assert "#123: Implement feature X" in result.output

    # Expected branch name with date suffix
    expected_branch = derive_branch_name_with_date("Implement feature X")

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
    assert "skipping branch/PR creation" in result.output

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
    assert "1 issue(s) submitted successfully!" in result.output
    # Verify workflow run URL is displayed (uses run_id returned by trigger_workflow)
    expected_url = "https://github.com/test-owner/test-repo/actions/runs/1234567890"
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


def test_close_orphaned_draft_prs_closes_old_drafts(tmp_path: Path) -> None:
    """Test _close_orphaned_draft_prs closes old draft PRs with erk-plan label."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Set up linked PRs:
    # - PR #100: old draft with erk-plan label (should be closed)
    # - PR #101: another old draft with erk-plan label (should be closed)
    # - PR #999: the new PR we just created (should NOT be closed)
    old_draft_pr = PullRequestInfo(
        number=100,
        state="OPEN",
        url="https://github.com/owner/repo/pull/100",
        is_draft=True,
        title="Old draft",
        checks_passing=None,
        owner="owner",
        repo="repo",
        labels=[ERK_PLAN_LABEL],
    )
    another_old_draft_pr = PullRequestInfo(
        number=101,
        state="OPEN",
        url="https://github.com/owner/repo/pull/101",
        is_draft=True,
        title="Another old draft",
        checks_passing=None,
        owner="owner",
        repo="repo",
        labels=[ERK_PLAN_LABEL],
    )
    new_pr = PullRequestInfo(
        number=999,
        state="OPEN",
        url="https://github.com/owner/repo/pull/999",
        is_draft=True,
        title="New PR",
        checks_passing=None,
        owner="owner",
        repo="repo",
        labels=[ERK_PLAN_LABEL],
    )

    fake_github = FakeGitHub(
        pr_issue_linkages={123: [old_draft_pr, another_old_draft_pr, new_pr]},
    )

    repo_dir = tmp_path / ".erk" / "repos" / "repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = ErkContext.for_test(
        cwd=repo_root,
        github=fake_github,
        repo=repo,
    )

    closed_prs = _close_orphaned_draft_prs(ctx, repo_root, issue_number=123, keep_pr_number=999)

    # Should close old drafts but not the new PR
    assert sorted(closed_prs) == [100, 101]
    assert sorted(fake_github.closed_prs) == [100, 101]


def test_close_orphaned_draft_prs_skips_non_drafts(tmp_path: Path) -> None:
    """Test _close_orphaned_draft_prs does NOT close non-draft PRs."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Old PR that is NOT a draft - should not be closed
    non_draft_pr = PullRequestInfo(
        number=100,
        state="OPEN",
        url="https://github.com/owner/repo/pull/100",
        is_draft=False,  # NOT a draft
        title="Ready for review",
        checks_passing=None,
        owner="owner",
        repo="repo",
        labels=[ERK_PLAN_LABEL],
    )

    fake_github = FakeGitHub(
        pr_issue_linkages={123: [non_draft_pr]},
    )

    repo_dir = tmp_path / ".erk" / "repos" / "repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = ErkContext.for_test(
        cwd=repo_root,
        github=fake_github,
        repo=repo,
    )

    closed_prs = _close_orphaned_draft_prs(ctx, repo_root, issue_number=123, keep_pr_number=999)

    # Non-draft PR should not be closed
    assert closed_prs == []
    assert fake_github.closed_prs == []


def test_close_orphaned_draft_prs_skips_already_closed(tmp_path: Path) -> None:
    """Test _close_orphaned_draft_prs does NOT close already-closed PRs."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Old draft that is already closed - should not be closed again
    closed_pr = PullRequestInfo(
        number=100,
        state="CLOSED",  # Already closed
        url="https://github.com/owner/repo/pull/100",
        is_draft=True,
        title="Old closed PR",
        checks_passing=None,
        owner="owner",
        repo="repo",
        labels=[ERK_PLAN_LABEL],
    )

    fake_github = FakeGitHub(
        pr_issue_linkages={123: [closed_pr]},
    )

    repo_dir = tmp_path / ".erk" / "repos" / "repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = ErkContext.for_test(
        cwd=repo_root,
        github=fake_github,
        repo=repo,
    )

    closed_prs = _close_orphaned_draft_prs(ctx, repo_root, issue_number=123, keep_pr_number=999)

    # Already-closed PR should not be closed again
    assert closed_prs == []
    assert fake_github.closed_prs == []


def test_close_orphaned_draft_prs_skips_prs_without_erk_plan_label(tmp_path: Path) -> None:
    """Test _close_orphaned_draft_prs does NOT close PRs without erk-plan label."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Old draft without erk-plan label - should not be closed
    pr_without_label = PullRequestInfo(
        number=100,
        state="OPEN",
        url="https://github.com/owner/repo/pull/100",
        is_draft=True,
        title="Unrelated draft PR",
        checks_passing=None,
        owner="owner",
        repo="repo",
        labels=["bug"],  # No erk-plan label
    )

    fake_github = FakeGitHub(
        pr_issue_linkages={123: [pr_without_label]},
    )

    repo_dir = tmp_path / ".erk" / "repos" / "repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = ErkContext.for_test(
        cwd=repo_root,
        github=fake_github,
        repo=repo,
    )

    closed_prs = _close_orphaned_draft_prs(ctx, repo_root, issue_number=123, keep_pr_number=999)

    # PR without erk-plan label should not be closed
    assert closed_prs == []
    assert fake_github.closed_prs == []


def test_close_orphaned_draft_prs_no_linked_prs(tmp_path: Path) -> None:
    """Test _close_orphaned_draft_prs handles no linked PRs gracefully."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # No PRs linked to the issue
    fake_github = FakeGitHub(
        pr_issue_linkages={},  # Empty
    )

    repo_dir = tmp_path / ".erk" / "repos" / "repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = ErkContext.for_test(
        cwd=repo_root,
        github=fake_github,
        repo=repo,
    )

    closed_prs = _close_orphaned_draft_prs(ctx, repo_root, issue_number=123, keep_pr_number=999)

    # No PRs to close
    assert closed_prs == []
    assert fake_github.closed_prs == []


def test_submit_closes_orphaned_draft_prs(tmp_path: Path) -> None:
    """Test submit command closes orphaned draft PRs after creating new one."""
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

    # Old orphaned draft PR linked to this issue
    old_draft_pr = PullRequestInfo(
        number=100,
        state="OPEN",
        url="https://github.com/test-owner/test-repo/pull/100",
        is_draft=True,
        title="Old draft",
        checks_passing=None,
        owner="test-owner",
        repo="test-repo",
        labels=[ERK_PLAN_LABEL],
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    fake_plan_store = FakePlanStore(plans={"123": plan})
    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
    )
    fake_github = FakeGitHub(
        pr_issue_linkages={123: [old_draft_pr]},
    )

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
    assert "Closed 1 orphaned draft PR(s): #100" in result.output

    # Verify old draft was closed
    assert fake_github.closed_prs == [100]


def test_submit_multiple_issues_success(tmp_path: Path) -> None:
    """Test submit successfully processes multiple issues."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)

    # Create two issues with erk-plan label
    issue1 = IssueInfo(
        number=123,
        title="Implement feature X",
        body="# Plan\n\nFeature X details...",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )
    issue2 = IssueInfo(
        number=456,
        title="Implement feature Y",
        body="# Plan\n\nFeature Y details...",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/456",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    plan1 = Plan(
        plan_identifier="123",
        title="Implement feature X",
        body="# Plan\n\nFeature X details...",
        state=PlanState.OPEN,
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
        metadata={},
    )
    plan2 = Plan(
        plan_identifier="456",
        title="Implement feature Y",
        body="# Plan\n\nFeature Y details...",
        state=PlanState.OPEN,
        url="https://github.com/test-owner/test-repo/issues/456",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
        metadata={},
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue1, 456: issue2})
    fake_plan_store = FakePlanStore(plans={"123": plan1, "456": plan2})
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
    result = runner.invoke(submit_cmd, ["123", "456"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "2 issue(s) submitted successfully!" in result.output
    assert "#123: Implement feature X" in result.output
    assert "#456: Implement feature Y" in result.output

    # Verify both branches were created and pushed
    assert len(fake_git.pushed_branches) == 2

    # Verify both PRs were created
    assert len(fake_github.created_prs) == 2

    # Verify both workflows were triggered
    assert len(fake_github.triggered_workflows) == 2
    workflow_issues = {inputs["issue_number"] for _, inputs in fake_github.triggered_workflows}
    assert workflow_issues == {"123", "456"}


def test_submit_multiple_issues_atomic_validation_failure(tmp_path: Path) -> None:
    """Test submit fails atomically when one issue is invalid - nothing submitted."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)

    # First issue is valid
    issue1 = IssueInfo(
        number=123,
        title="Implement feature X",
        body="# Plan\n\nFeature X details...",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )
    # Second issue is CLOSED (invalid)
    issue2 = IssueInfo(
        number=456,
        title="Implement feature Y",
        body="# Plan\n\nFeature Y details...",
        state="CLOSED",
        url="https://github.com/test-owner/test-repo/issues/456",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue1, 456: issue2})
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
    result = runner.invoke(submit_cmd, ["123", "456"], obj=ctx)

    # Should fail because second issue is closed
    assert result.exit_code == 1
    assert "is CLOSED" in result.output

    # CRITICAL: Verify NOTHING was submitted (atomic validation)
    assert len(fake_git.pushed_branches) == 0
    assert len(fake_github.created_prs) == 0
    assert len(fake_github.triggered_workflows) == 0


def test_submit_single_issue_still_works(tmp_path: Path) -> None:
    """Test submit still works with a single issue (backwards compatibility)."""
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
    # Single issue still works with new nargs=-1 signature
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "1 issue(s) submitted successfully!" in result.output
    assert "#123: Implement feature X" in result.output

    # Verify single issue was processed
    assert len(fake_git.pushed_branches) == 1
    assert len(fake_github.created_prs) == 1
    assert len(fake_github.triggered_workflows) == 1


def test_submit_requires_at_least_one_issue() -> None:
    """Test submit requires at least one issue number argument."""
    runner = CliRunner()
    result = runner.invoke(submit_cmd, [])

    # Should fail with usage error (no arguments provided)
    assert result.exit_code != 0
    assert "Missing argument" in result.output or "Usage:" in result.output


def test_validate_issue_for_submit_returns_validated_issue(tmp_path: Path) -> None:
    """Test _validate_issue_for_submit returns ValidatedIssue with correct fields."""
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

    validated = _validate_issue_for_submit(ctx, repo, 123)

    assert isinstance(validated, ValidatedIssue)
    assert validated.number == 123
    assert validated.issue == issue
    assert validated.branch_name.startswith("implement-feature-x-")
    assert validated.branch_exists is False
    assert validated.pr_number is None
