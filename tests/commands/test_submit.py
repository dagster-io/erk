"""Tests for erk submit command."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo
from erk_shared.github.issues.types import PRReference
from erk_shared.github.metadata import MetadataBlock, render_metadata_block
from erk_shared.plan_store.fake import FakePlanStore
from erk_shared.plan_store.types import Plan, PlanState

from erk.cli.commands.submit import (
    ERK_PLAN_LABEL,
    _close_orphaned_draft_prs,
    _ensure_unique_branch_name,
    _strip_plan_markers,
    submit_cmd,
)
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
from tests.fakes.issue_link_branches import FakeIssueLinkBranches


def _make_plan_body(content: str = "Implementation details...") -> str:
    """Create a valid issue body with plan-header metadata block.

    The plan-header block is required for `update_plan_header_dispatch` to work.
    """
    plan_header_data = {
        "schema_version": "2",
        "created_at": "2024-01-01T00:00:00Z",
        "created_by": "test-user",
    }
    header_block = render_metadata_block(MetadataBlock("plan-header", plan_header_data))
    return f"{header_block}\n\n# Plan\n\n{content}"


def test_submit_creates_branch_and_draft_pr(tmp_path: Path) -> None:
    """Test submit creates linked branch, pushes, creates draft PR, triggers workflow."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create issue with erk-plan label, OPEN state
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body=_make_plan_body(),
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
        body=_make_plan_body(),
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
    fake_issue_dev = FakeIssueLinkBranches()

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
        issue_link_branches=fake_issue_dev,
        plan_store=fake_plan_store,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "issue(s) submitted successfully!" in result.output
    assert "Workflow:" in result.output

    # Branch name is sanitize_worktree_name(...) + timestamp suffix "-01-15-1430"
    expected_branch = "123-implement-feature-x-01-15-1430"

    # Verify branch was created via gh issue develop
    assert fake_issue_dev.created_branches == [(123, expected_branch)]

    # Verify branch was pushed
    assert len(fake_git.pushed_branches) == 1
    remote, branch, set_upstream = fake_git.pushed_branches[0]
    assert remote == "origin"
    assert branch == expected_branch
    assert set_upstream is True

    # Verify draft PR was created
    assert len(fake_github.created_prs) == 1
    branch_name, title, body, base, draft = fake_github.created_prs[0]
    assert branch_name == expected_branch
    assert title == "Implement feature X"
    assert draft is True
    # PR body contains plan reference (not Closes #N - handled by native branch linking)
    assert "**Plan:** #123" in body

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
        body=_make_plan_body(),
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    # Pre-existing branch from previous gh issue develop
    expected_branch = "123-existing-branch"

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    # FakeIssueLinkBranches with existing branch for issue 123
    fake_issue_dev = FakeIssueLinkBranches(existing_branches={123: expected_branch})
    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
        # Simulate branch existing on remote
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
        issue_link_branches=fake_issue_dev,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "PR #456 already exists" in result.output
    assert "Skipping branch/PR creation" in result.output

    # Verify no new branch was created (existing branch was reused)
    assert fake_issue_dev.created_branches == []

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
        body=_make_plan_body(),
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
        body=_make_plan_body(),
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
        body=_make_plan_body(),
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
    assert "issue(s) submitted successfully!" in result.output
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
        body=_make_plan_body(),
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
        body=_make_plan_body(),
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
        body=_make_plan_body(),
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
    """Test _close_orphaned_draft_prs closes old draft PRs linked to issue."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Set up linked PRs:
    # - PR #100: old draft (should be closed)
    # - PR #101: another old draft (should be closed)
    # - PR #999: the new PR we just created (should NOT be closed)
    old_draft_pr = PRReference(number=100, state="OPEN", is_draft=True)
    another_old_draft_pr = PRReference(number=101, state="OPEN", is_draft=True)
    new_pr = PRReference(number=999, state="OPEN", is_draft=True)

    fake_github = FakeGitHub()
    fake_issues = FakeGitHubIssues(
        pr_references={123: [old_draft_pr, another_old_draft_pr, new_pr]},
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
        issues=fake_issues,
        repo=repo,
    )

    closed_prs = _close_orphaned_draft_prs(
        ctx,
        repo_root,
        issue_number=123,
        keep_pr_number=999,
    )

    # Should close old drafts but not the new PR
    assert sorted(closed_prs) == [100, 101]
    assert sorted(fake_github.closed_prs) == [100, 101]


def test_close_orphaned_draft_prs_skips_non_drafts(tmp_path: Path) -> None:
    """Test _close_orphaned_draft_prs does NOT close non-draft PRs."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Old PR that is NOT a draft - should not be closed
    non_draft_pr = PRReference(number=100, state="OPEN", is_draft=False)

    fake_github = FakeGitHub()
    fake_issues = FakeGitHubIssues(
        pr_references={123: [non_draft_pr]},
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
        issues=fake_issues,
        repo=repo,
    )

    closed_prs = _close_orphaned_draft_prs(
        ctx,
        repo_root,
        issue_number=123,
        keep_pr_number=999,
    )

    # Non-draft PR should not be closed
    assert closed_prs == []
    assert fake_github.closed_prs == []


def test_close_orphaned_draft_prs_skips_already_closed(tmp_path: Path) -> None:
    """Test _close_orphaned_draft_prs does NOT close already-closed PRs."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Old draft that is already closed - should not be closed again
    closed_pr = PRReference(number=100, state="CLOSED", is_draft=True)

    fake_github = FakeGitHub()
    fake_issues = FakeGitHubIssues(
        pr_references={123: [closed_pr]},
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
        issues=fake_issues,
        repo=repo,
    )

    closed_prs = _close_orphaned_draft_prs(
        ctx,
        repo_root,
        issue_number=123,
        keep_pr_number=999,
    )

    # Already-closed PR should not be closed again
    assert closed_prs == []
    assert fake_github.closed_prs == []


def test_close_orphaned_draft_prs_no_linked_prs(tmp_path: Path) -> None:
    """Test _close_orphaned_draft_prs handles no linked PRs gracefully."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # No PRs linked to the issue
    fake_issues = FakeGitHubIssues(
        pr_references={},  # Empty
    )
    fake_github = FakeGitHub()

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
        issues=fake_issues,
        repo=repo,
    )

    closed_prs = _close_orphaned_draft_prs(
        ctx,
        repo_root,
        issue_number=123,
        keep_pr_number=999,
    )

    # No PRs to close
    assert closed_prs == []
    assert fake_github.closed_prs == []


def test_submit_creates_pr_when_branch_exists_but_no_pr(tmp_path: Path) -> None:
    """Test submit adds empty commit and creates PR when branch exists but no PR."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body=_make_plan_body(),
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    # Pre-existing branch from previous gh issue develop (no PR though)
    expected_branch = "123-existing-branch"

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    # FakeIssueLinkBranches with existing branch for issue 123
    fake_issue_dev = FakeIssueLinkBranches(existing_branches={123: expected_branch})
    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
        # Simulate branch existing on remote
        remote_branches={repo_root: [f"origin/{expected_branch}"]},
    )
    # No PR status for this branch (pr_statuses is empty)
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
        issue_link_branches=fake_issue_dev,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "exists but no PR. Adding placeholder commit" in result.output
    assert "Placeholder commit pushed" in result.output
    assert "Draft PR #999 created" in result.output
    assert "Local branch cleaned up" in result.output

    # Verify no new branch was created via gh issue develop (existing branch was reused)
    assert fake_issue_dev.created_branches == []

    # Verify empty commit was created
    assert len(fake_git.commits) == 1
    cwd, message, staged_files = fake_git.commits[0]
    assert "[erk-plan] Initialize implementation for issue #123" in message
    assert staged_files == []  # Empty commit has no staged files

    # Verify branch was pushed after commit
    assert len(fake_git.pushed_branches) == 1
    remote, branch, set_upstream = fake_git.pushed_branches[0]
    assert remote == "origin"
    assert branch == expected_branch

    # Verify draft PR was created
    assert len(fake_github.created_prs) == 1
    branch_name, title, body, base, draft = fake_github.created_prs[0]
    assert branch_name == expected_branch
    assert title == "Implement feature X"
    assert draft is True
    # PR body contains plan reference (not Closes #N - handled by native branch linking)
    assert "**Plan:** #123" in body

    # Verify PR body was updated with checkout footer
    assert len(fake_github.updated_pr_bodies) == 1
    pr_number, updated_body = fake_github.updated_pr_bodies[0]
    assert pr_number == 999
    assert "erk pr checkout 999" in updated_body

    # Verify local branch was cleaned up (checkout original, delete local)
    assert len(fake_git._checked_out_branches) == 2  # branch checkout + restore to original
    assert len(fake_git._deleted_branches) == 1
    assert expected_branch in fake_git._deleted_branches

    # Workflow should still be triggered
    assert len(fake_github.triggered_workflows) == 1


def test_submit_closes_orphaned_draft_prs(tmp_path: Path) -> None:
    """Test submit command closes orphaned draft PRs after creating new one."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body=_make_plan_body(),
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
        body=_make_plan_body(),
        state=PlanState.OPEN,
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
        metadata={},
    )

    # Old orphaned draft PR linked to this issue
    old_draft_pr = PRReference(
        number=100,
        state="OPEN",
        is_draft=True,
    )

    fake_github_issues = FakeGitHubIssues(
        issues={123: issue},
        pr_references={123: [old_draft_pr]},
    )
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
    assert "Closed 1 orphaned draft PR(s): #100" in result.output

    # Verify old draft was closed
    assert fake_github.closed_prs == [100]


def test_ensure_unique_branch_name_returns_original_when_available(tmp_path: Path) -> None:
    """Test _ensure_unique_branch_name returns original name if not on remote."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # No remote branches configured - name is available
    fake_git = FakeGit(remote_branches={repo_root: []})

    repo_dir = tmp_path / ".erk" / "repos" / "repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = ErkContext.for_test(cwd=repo_root, git=fake_git, repo=repo)

    result = _ensure_unique_branch_name(ctx, repo_root, "123-feature-11-30-1200")

    assert result == "123-feature-11-30-1200"


def test_ensure_unique_branch_name_adds_suffix_on_collision(tmp_path: Path) -> None:
    """Test _ensure_unique_branch_name adds -1 suffix when branch exists."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Branch already exists on remote
    fake_git = FakeGit(remote_branches={repo_root: ["origin/123-feature-11-30-1200"]})

    repo_dir = tmp_path / ".erk" / "repos" / "repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = ErkContext.for_test(cwd=repo_root, git=fake_git, repo=repo)

    result = _ensure_unique_branch_name(ctx, repo_root, "123-feature-11-30-1200")

    assert result == "123-feature-11-30-1200-1"


def test_ensure_unique_branch_name_increments_suffix(tmp_path: Path) -> None:
    """Test _ensure_unique_branch_name increments suffix until unique."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Base name AND -1 suffix already exist
    fake_git = FakeGit(
        remote_branches={
            repo_root: [
                "origin/123-feature-11-30-1200",
                "origin/123-feature-11-30-1200-1",
                "origin/123-feature-11-30-1200-2",
            ]
        }
    )

    repo_dir = tmp_path / ".erk" / "repos" / "repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = ErkContext.for_test(cwd=repo_root, git=fake_git, repo=repo)

    result = _ensure_unique_branch_name(ctx, repo_root, "123-feature-11-30-1200")

    assert result == "123-feature-11-30-1200-3"


def test_submit_handles_local_branch_already_exists(tmp_path: Path) -> None:
    """Test submit handles case where branch exists on remote AND locally.

    This tests the scenario where a previous failed run left a local branch
    that wasn't cleaned up. The command should not crash when trying to
    create a tracking branch that already exists locally.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body=_make_plan_body(),
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    # Pre-existing branch from previous gh issue develop (no PR though)
    expected_branch = "123-existing-branch"

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    # FakeIssueLinkBranches with existing branch for issue 123
    fake_issue_dev = FakeIssueLinkBranches(existing_branches={123: expected_branch})
    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
        # Branch exists on remote
        remote_branches={repo_root: [f"origin/{expected_branch}"]},
        # Branch ALSO exists locally (e.g., from previous failed run)
        local_branches={repo_root: [expected_branch]},
    )
    # No PR status for this branch (pr_statuses is empty)
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
        issue_link_branches=fake_issue_dev,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    # Should succeed without crashing
    assert result.exit_code == 0, result.output
    assert "exists but no PR. Adding placeholder commit" in result.output
    assert "Placeholder commit pushed" in result.output
    assert "Draft PR #999 created" in result.output

    # Verify no tracking branch was created (since local branch already exists)
    assert fake_git.created_tracking_branches == []

    # Verify branch was still checked out (reusing existing local branch)
    assert (repo_root, expected_branch) in fake_git._checked_out_branches

    # Verify commit was created
    assert len(fake_git.commits) == 1

    # Workflow should still be triggered
    assert len(fake_github.triggered_workflows) == 1


def test_submit_handles_branch_name_collision(tmp_path: Path) -> None:
    """Test submit adds numeric suffix when branch already exists on remote."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="My Feature",
        body=_make_plan_body(),
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    plan = Plan(
        plan_identifier="123",
        title="My Feature",
        body=_make_plan_body(),
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

    # The expected branch name based on sanitize_worktree_name + timestamp suffix
    # "123-my-feature" + "-01-15-1430" = "123-my-feature-01-15-1430"
    # Simulate this branch already existing on remote
    expected_base_branch = "123-my-feature-01-15-1430"

    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
        # The base branch name already exists on remote
        remote_branches={repo_root: [f"origin/{expected_base_branch}"]},
    )
    fake_github = FakeGitHub()
    fake_issue_dev = FakeIssueLinkBranches()

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
        issue_link_branches=fake_issue_dev,
        plan_store=fake_plan_store,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "issue(s) submitted successfully!" in result.output

    # Verify branch was created with -1 suffix due to collision
    expected_branch_with_suffix = f"{expected_base_branch}-1"
    assert fake_issue_dev.created_branches == [(123, expected_branch_with_suffix)]

    # Verify branch was pushed with the suffixed name
    assert len(fake_git.pushed_branches) == 1
    remote, branch, set_upstream = fake_git.pushed_branches[0]
    assert remote == "origin"
    assert branch == expected_branch_with_suffix
    assert set_upstream is True


def test_submit_multiple_issues_success(tmp_path: Path) -> None:
    """Test submit successfully handles multiple issue numbers (happy path)."""
    import shutil

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)
    # Create two valid issues with erk-plan label
    issue_123 = IssueInfo(
        number=123,
        title="Feature A",
        body=_make_plan_body("Implementation for A..."),
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )
    issue_456 = IssueInfo(
        number=456,
        title="Feature B",
        body=_make_plan_body("Implementation for B..."),
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/456",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    plan_123 = Plan(
        plan_identifier="123",
        title="Feature A",
        body=_make_plan_body("Implementation for A..."),
        state=PlanState.OPEN,
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
        metadata={},
    )
    plan_456 = Plan(
        plan_identifier="456",
        title="Feature B",
        body=_make_plan_body("Implementation for B..."),
        state=PlanState.OPEN,
        url="https://github.com/test-owner/test-repo/issues/456",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
        metadata={},
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue_123, 456: issue_456})
    fake_plan_store = FakePlanStore(plans={"123": plan_123, "456": plan_456})

    # Create a custom FakeGit that cleans up .worker-impl/ on branch checkout
    # This simulates the real behavior where checking out a branch without
    # .worker-impl/ removes the folder from the working directory
    class FakeGitWithCheckoutCleanup(FakeGit):
        def checkout_branch(self, cwd: Path, branch_name: str) -> None:
            super().checkout_branch(cwd, branch_name)
            # Simulate git checkout: when switching to original branch,
            # files from the feature branch (like .worker-impl/) are removed
            worker_impl = cwd / ".worker-impl"
            if worker_impl.exists():
                shutil.rmtree(worker_impl)

    fake_git = FakeGitWithCheckoutCleanup(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
    )
    fake_github = FakeGitHub()
    fake_issue_dev = FakeIssueLinkBranches()

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
        issue_link_branches=fake_issue_dev,
        plan_store=fake_plan_store,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123", "456"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "2 issue(s) submitted successfully!" in result.output
    assert "#123: Feature A" in result.output
    assert "#456: Feature B" in result.output

    # Verify both branches were created
    assert len(fake_issue_dev.created_branches) == 2
    issue_numbers_created = [b[0] for b in fake_issue_dev.created_branches]
    assert 123 in issue_numbers_created
    assert 456 in issue_numbers_created

    # Verify both workflows were triggered
    assert len(fake_github.triggered_workflows) == 2


def test_submit_multiple_issues_atomic_validation_failure(tmp_path: Path) -> None:
    """Test atomic validation: if second issue is invalid, nothing is submitted."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)
    # First issue is valid
    issue_123 = IssueInfo(
        number=123,
        title="Feature A",
        body=_make_plan_body("Implementation for A..."),
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )
    # Second issue is CLOSED (invalid)
    issue_456 = IssueInfo(
        number=456,
        title="Feature B",
        body=_make_plan_body("Implementation for B..."),
        state="CLOSED",
        url="https://github.com/test-owner/test-repo/issues/456",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue_123, 456: issue_456})
    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
    )
    fake_github = FakeGitHub()
    fake_issue_dev = FakeIssueLinkBranches()

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
        issue_link_branches=fake_issue_dev,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123", "456"], obj=ctx)

    # Should fail on the second issue validation
    assert result.exit_code == 1
    assert "is CLOSED" in result.output or "Cannot submit closed issues" in result.output

    # Critical: First issue validated and created branch, but validation happens before submission
    # The branch was created during validation, but workflow was NOT triggered
    assert len(fake_github.triggered_workflows) == 0


def test_submit_single_issue_still_works(tmp_path: Path) -> None:
    """Test backwards compatibility: single issue argument still works."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body=_make_plan_body(),
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
        body=_make_plan_body(),
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
    fake_issue_dev = FakeIssueLinkBranches()

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
        issue_link_branches=fake_issue_dev,
        plan_store=fake_plan_store,
        repo=repo,
    )

    runner = CliRunner()
    # Single argument - backwards compatibility
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "1 issue(s) submitted successfully!" in result.output
    assert "Workflow:" in result.output

    # Verify branch was created
    assert len(fake_issue_dev.created_branches) == 1

    # Verify workflow was triggered
    assert len(fake_github.triggered_workflows) == 1


def test_submit_updates_dispatch_info_in_issue(tmp_path: Path) -> None:
    """Test submit updates issue body with dispatch info after triggering workflow."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body=_make_plan_body(),
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
        body=_make_plan_body(),
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
    fake_issue_dev = FakeIssueLinkBranches()

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
        issue_link_branches=fake_issue_dev,
        plan_store=fake_plan_store,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "Dispatch metadata written to issue" in result.output

    # Verify issue body was updated with dispatch info
    updated_issue = fake_github_issues.get_issue(repo_root, 123)
    assert "last_dispatched_run_id: '1234567890'" in updated_issue.body
    assert "last_dispatched_node_id: WFR_fake_node_id_1234567890" in updated_issue.body
    assert "last_dispatched_at:" in updated_issue.body


def test_submit_warns_when_node_id_not_available(tmp_path: Path) -> None:
    """Test submit warns but continues when workflow run node_id cannot be fetched."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body=_make_plan_body(),
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
        body=_make_plan_body(),
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

    # Create a custom FakeGitHub that returns None for node_id lookup
    class FakeGitHubNoNodeId(FakeGitHub):
        def get_workflow_run_node_id(self, repo_root: Path, run_id: str) -> None:
            # Return None to simulate failure to fetch node_id
            return None

    fake_github = FakeGitHubNoNodeId()
    fake_issue_dev = FakeIssueLinkBranches()

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
        issue_link_branches=fake_issue_dev,
        plan_store=fake_plan_store,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    # Should succeed but warn about missing node_id
    assert result.exit_code == 0, result.output
    assert "Could not fetch workflow run node_id" in result.output
    # Workflow should still be triggered successfully
    assert "1 issue(s) submitted successfully!" in result.output


def test_submit_with_custom_base_branch(tmp_path: Path) -> None:
    """Test submit creates PR with custom base branch when --base is specified."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create issue with erk-plan label, OPEN state
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body=_make_plan_body(),
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
        body=_make_plan_body(),
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
        # Custom feature branch exists on remote
        remote_branches={repo_root: ["origin/feature/parent-branch"]},
    )
    fake_github = FakeGitHub()
    fake_issue_dev = FakeIssueLinkBranches()

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
        issue_link_branches=fake_issue_dev,
        plan_store=fake_plan_store,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123", "--base", "feature/parent-branch"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "issue(s) submitted successfully!" in result.output

    # Verify PR was created with custom base branch
    assert len(fake_github.created_prs) == 1
    branch_name, title, body, base, draft = fake_github.created_prs[0]
    assert base == "feature/parent-branch"  # NOT "master"

    # Verify development branch was created from custom base
    assert len(fake_issue_dev.created_branches) == 1
    issue_num, branch = fake_issue_dev.created_branches[0]
    assert issue_num == 123
    # Verify the development branch was created with the custom base
    # (FakeIssueLinkBranches records all calls in create_calls)
    assert len(fake_issue_dev.create_calls) == 1
    call = fake_issue_dev.create_calls[0]
    assert call.base_branch == "feature/parent-branch"


def test_submit_with_invalid_base_branch(tmp_path: Path) -> None:
    """Test submit fails early when --base branch doesn't exist on remote (LBYL)."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create issue (we won't get to validation because base branch check fails first)
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body=_make_plan_body(),
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
        # "nonexistent-branch" does NOT exist on remote
        remote_branches={repo_root: []},
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
    result = runner.invoke(submit_cmd, ["123", "--base", "nonexistent-branch"], obj=ctx)

    # Should fail early with error (LBYL)
    assert result.exit_code == 1
    assert "Error: Base branch 'nonexistent-branch' does not exist on remote" in result.output

    # Verify workflow was NOT triggered (failure happened before workflow dispatch)
    assert len(fake_github.triggered_workflows) == 0
