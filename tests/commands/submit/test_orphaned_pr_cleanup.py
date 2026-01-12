"""Tests for closing orphaned draft PRs during submit."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import _close_orphaned_draft_prs, submit_cmd
from erk.core.context import context_for_test
from erk.core.repo_discovery import RepoContext
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.github.issues.types import PRReference
from tests.commands.submit.conftest import create_plan, setup_submit_context


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
        pool_json_path=repo_dir / "pool.json",
    )
    ctx = context_for_test(
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
        pool_json_path=repo_dir / "pool.json",
    )
    ctx = context_for_test(
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
        pool_json_path=repo_dir / "pool.json",
    )
    ctx = context_for_test(
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
        pool_json_path=repo_dir / "pool.json",
    )
    ctx = context_for_test(
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
    plan = create_plan("123", "Implement feature X")

    # Old orphaned draft PR linked to this issue
    old_draft_pr = PRReference(
        number=100,
        state="OPEN",
        is_draft=True,
    )

    ctx, fake_git, fake_github, fake_github_issues, _, _ = setup_submit_context(
        tmp_path, {"123": plan}
    )
    # Add pr_references to the fake issues
    fake_github_issues._pr_references = {123: [old_draft_pr]}

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "Closed 1 orphaned draft PR(s): #100" in result.output

    # Verify old draft was closed
    assert fake_github.closed_prs == [100]
