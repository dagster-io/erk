"""Tests for erk submit command."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo
from erk_shared.github.issues.types import PRReference
from erk_shared.github.metadata import MetadataBlock, render_metadata_block
from erk_shared.integrations.gt.operations.finalize import ERK_SKIP_EXTRACTION_LABEL
from erk_shared.plan_store.fake import FakePlanStore
from erk_shared.plan_store.types import Plan, PlanState

from erk.cli.commands.submit import (
    ERK_PLAN_LABEL,
    _close_orphaned_draft_prs,
    _strip_plan_markers,
    is_issue_extraction_plan,
    load_workflow_config,
    submit_cmd,
)
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext


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


def _make_extraction_plan_body(content: str = "Documentation extraction...") -> str:
    """Create a valid extraction plan issue body with plan-header metadata block.

    The plan-header block with plan_type: "extraction" is used to identify PRs
    that originate from extraction plans.
    """
    plan_header_data = {
        "schema_version": "2",
        "created_at": "2024-01-01T00:00:00Z",
        "created_by": "test-user",
        "plan_type": "extraction",
        "source_plan_issues": [100],
        "extraction_session_ids": ["session-abc"],
    }
    header_block = render_metadata_block(MetadataBlock("plan-header", plan_header_data))
    return f"{header_block}\n\n# Extraction Plan\n\n{content}"


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
    assert "Workflow:" in result.output

    # Branch name is sanitize_worktree_name(...) + timestamp suffix "-01-15-1430"
    expected_branch = "P123-implement-feature-x-01-15-1430"

    # Verify branch was created via git (from origin/<current_branch>)
    # Note: submit defaults to current branch as base, not trunk_branch
    assert len(fake_git.created_branches) == 1
    created_repo, created_branch, created_base = fake_git.created_branches[0]
    assert created_repo == repo_root
    assert created_branch == expected_branch
    assert created_base == "origin/main"  # Uses current branch as base

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
    # PR body contains plan reference
    assert "**Plan:** #123" in body

    # Verify workflow was triggered
    assert len(fake_github.triggered_workflows) == 1
    workflow, inputs = fake_github.triggered_workflows[0]
    assert workflow == "erk-impl.yml"
    assert inputs["issue_number"] == "123"

    # Verify local branch was cleaned up
    assert len(fake_git._deleted_branches) == 1
    assert expected_branch in fake_git._deleted_branches


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

    # Verify PR body was updated with checkout footer (includes && erk pr sync)
    assert len(fake_github.updated_pr_bodies) == 1
    pr_number, updated_body = fake_github.updated_pr_bodies[0]
    assert pr_number == 999  # FakeGitHub returns 999 for created PRs
    assert "erk pr checkout 999 && erk pr sync" in updated_body


def test_submit_includes_closes_issue_in_pr_body(tmp_path: Path) -> None:
    """Test submit includes 'Closes #N' in INITIAL PR body to enable willCloseTarget.

    GitHub's willCloseTarget API field is set at PR creation time and is NOT updated
    when the PR body is edited afterward. This test verifies that 'Closes #N' is
    included in the body passed to create_pr(), not just added via update_pr_body().
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

    # CRITICAL: Verify "Closes #123" is in the INITIAL body passed to create_pr()
    # GitHub's willCloseTarget API field is set at creation time and NOT updated afterward
    assert len(fake_github.created_prs) == 1
    branch, title, initial_body, base, draft = fake_github.created_prs[0]
    assert "Closes #123" in initial_body, (
        "Closes #123 must be in initial PR body for GitHub's willCloseTarget to work"
    )

    # Verify PR body was also updated (to add checkout command footer)
    assert len(fake_github.updated_pr_bodies) == 1
    pr_number, updated_body = fake_github.updated_pr_bodies[0]
    assert pr_number == 999  # FakeGitHub returns 999 for created PRs
    assert "Closes #123" in updated_body
    assert "erk pr checkout 999 && erk pr sync" in updated_body


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
    assert "#123: Feature A" in result.output
    assert "#456: Feature B" in result.output

    # Verify both branches were created via git
    assert len(fake_git.created_branches) == 2
    created_branch_names = [b[1] for b in fake_git.created_branches]
    # Branch names include issue number prefix
    assert any("123-" in name for name in created_branch_names)
    assert any("456-" in name for name in created_branch_names)

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
    # Single argument - backwards compatibility
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "1 issue(s) submitted successfully!" in result.output
    assert "Workflow:" in result.output

    # Verify branch was created via git
    assert len(fake_git.created_branches) == 1

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
    result = runner.invoke(submit_cmd, ["123", "--base", "feature/parent-branch"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "issue(s) submitted successfully!" in result.output

    # Verify PR was created with custom base branch
    assert len(fake_github.created_prs) == 1
    branch_name, title, body, base, draft = fake_github.created_prs[0]
    assert base == "feature/parent-branch"  # NOT "master"

    # Verify branch was created via git (FakeGit tracks created branches)
    assert len(fake_git.created_branches) == 1
    created_repo, created_branch, created_base = fake_git.created_branches[0]
    assert created_repo == repo_root
    assert created_base == "origin/feature/parent-branch"


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


def test_is_issue_extraction_plan_returns_true_for_extraction_plan() -> None:
    """Test is_issue_extraction_plan returns True when plan_type is 'extraction'."""
    body = _make_extraction_plan_body()
    result = is_issue_extraction_plan(body)
    assert result is True


def test_is_issue_extraction_plan_returns_false_for_standard_plan() -> None:
    """Test is_issue_extraction_plan returns False when plan_type is not 'extraction'."""
    body = _make_plan_body()
    result = is_issue_extraction_plan(body)
    assert result is False


def test_is_issue_extraction_plan_returns_false_for_no_metadata() -> None:
    """Test is_issue_extraction_plan returns False when there's no plan-header block."""
    body = "# Just a plain issue\n\nNo metadata here."
    result = is_issue_extraction_plan(body)
    assert result is False


def test_submit_extraction_plan_adds_skip_extraction_label(tmp_path: Path) -> None:
    """Test submit adds erk-skip-extraction label to PR for extraction plans."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)
    # Issue with extraction plan_type in metadata
    extraction_body = _make_extraction_plan_body()
    issue = IssueInfo(
        number=123,
        title="Extract documentation from session X",
        body=extraction_body,
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    plan = Plan(
        plan_identifier="123",
        title="Extract documentation from session X",
        body=extraction_body,
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

    # Verify erk-skip-extraction label was added to PR
    assert len(fake_github.added_labels) == 1
    pr_number, label = fake_github.added_labels[0]
    assert pr_number == 999  # FakeGitHub returns 999 for created PRs
    assert label == ERK_SKIP_EXTRACTION_LABEL

    # Verify PR body was updated (checkout command, no extraction marker)
    assert len(fake_github.updated_pr_bodies) == 1
    _, updated_body = fake_github.updated_pr_bodies[0]
    assert "erk pr checkout" in updated_body


def test_submit_standard_plan_does_not_add_skip_extraction_label(tmp_path: Path) -> None:
    """Test submit does NOT add erk-skip-extraction label for standard plans."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)
    # Standard plan (not extraction)
    standard_body = _make_plan_body()
    issue = IssueInfo(
        number=456,
        title="Implement feature Y",
        body=standard_body,
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/456",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    plan = Plan(
        plan_identifier="456",
        title="Implement feature Y",
        body=standard_body,
        state=PlanState.OPEN,
        url="https://github.com/test-owner/test-repo/issues/456",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
        metadata={},
    )

    fake_github_issues = FakeGitHubIssues(issues={456: issue})
    fake_plan_store = FakePlanStore(plans={"456": plan})
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
    result = runner.invoke(submit_cmd, ["456"], obj=ctx)

    assert result.exit_code == 0, result.output

    # Verify NO label was added (standard plan, not extraction)
    assert len(fake_github.added_labels) == 0

    # Verify PR body was updated (checkout command only)
    assert len(fake_github.updated_pr_bodies) == 1
    _, updated_body = fake_github.updated_pr_bodies[0]
    assert "erk pr checkout" in updated_body


def test_load_workflow_config_file_not_found(tmp_path: Path) -> None:
    """Test load_workflow_config returns empty dict when config file doesn't exist."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    result = load_workflow_config(repo_root, "erk-impl.yml")

    assert result == {}


def test_load_workflow_config_valid_toml(tmp_path: Path) -> None:
    """Test load_workflow_config returns string dict from valid TOML."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create workflow config file
    config_dir = repo_root / ".erk" / "workflows"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "dispatch-erk-queue.toml"
    config_file.write_text(
        'kit_names = "erk,gt,devrun"\n'
        'model_name = "claude-sonnet-4-5-20250929"\n'
        'package_install_script = ""\n',
        encoding="utf-8",
    )

    result = load_workflow_config(repo_root, "erk/dispatch-erk-queue.yml")

    assert result == {
        "kit_names": "erk,gt,devrun",
        "model_name": "claude-sonnet-4-5-20250929",
        "package_install_script": "",
    }


def test_load_workflow_config_converts_values_to_strings(tmp_path: Path) -> None:
    """Test load_workflow_config converts non-string values to strings."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create workflow config file with non-string values
    config_dir = repo_root / ".erk" / "workflows"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "my-workflow.toml"
    config_file.write_text(
        'timeout = 300\nenabled = true\nname = "test"\n',
        encoding="utf-8",
    )

    result = load_workflow_config(repo_root, "my-workflow.yml")

    # All values should be strings
    assert result == {
        "timeout": "300",
        "enabled": "True",
        "name": "test",
    }


def test_load_workflow_config_strips_yml_extension(tmp_path: Path) -> None:
    """Test load_workflow_config strips .yml extension from workflow name."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    config_dir = repo_root / ".erk" / "workflows"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "my-workflow.toml"
    config_file.write_text('key = "value"\n', encoding="utf-8")

    # Pass with .yml extension
    result = load_workflow_config(repo_root, "my-workflow.yml")

    assert result == {"key": "value"}


def test_load_workflow_config_strips_yaml_extension(tmp_path: Path) -> None:
    """Test load_workflow_config strips .yaml extension from workflow name."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    config_dir = repo_root / ".erk" / "workflows"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "my-workflow.toml"
    config_file.write_text('key = "value"\n', encoding="utf-8")

    # Pass with .yaml extension
    result = load_workflow_config(repo_root, "my-workflow.yaml")

    assert result == {"key": "value"}


def test_submit_uses_workflow_config(tmp_path: Path) -> None:
    """Test submit includes workflow config inputs when triggering workflow."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create workflow config file
    config_dir = repo_root / ".erk" / "workflows"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "erk-impl.toml"
    config_file.write_text(
        'kit_names = "erk,gt,devrun"\nmodel_name = "claude-sonnet-4-5-20250929"\n',
        encoding="utf-8",
    )

    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Test with workflow config",
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
        title="Test with workflow config",
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

    # Verify workflow was triggered with config inputs
    assert len(fake_github.triggered_workflows) == 1
    workflow, inputs = fake_github.triggered_workflows[0]
    assert workflow == "erk-impl.yml"
    # Required inputs
    assert inputs["issue_number"] == "123"
    assert inputs["submitted_by"] == "test-user"
    # Config-based inputs from .erk/workflows/erk-impl.toml
    assert inputs["kit_names"] == "erk,gt,devrun"
    assert inputs["model_name"] == "claude-sonnet-4-5-20250929"
