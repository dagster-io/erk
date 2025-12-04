"""Tests for execute_submit_pr operation.

This operation orchestrates the full PR submission workflow:
1. Preflight (auth, squash, submit to Graphite, extract diff)
2. AI Generation (commit message via ClaudeCLIExecutor)
3. Finalize (update PR metadata)
"""

from pathlib import Path

from erk_shared.integrations.claude.fake import FakeClaudeExecutor
from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.submit_pr import execute_submit_pr
from erk_shared.integrations.gt.types import SubmitPRError, SubmitPRResult

from tests.unit.kits.gt.fake_ops import FakeGtKitOps


def test_submit_pr_success(tmp_path: Path) -> None:
    """Test successful end-to-end PR submission."""
    claude = FakeClaudeExecutor(
        title="feat: Add new widget component",
        body="This PR adds a reusable widget component for the dashboard.",
    )
    ops = (
        FakeGtKitOps(claude_executor=claude)
        .with_repo_root(str(tmp_path))
        .with_branch("feature-widget", parent="main")
        .with_commits(1)
        .with_pr(42, url="https://github.com/org/repo/pull/42")
    )

    result = render_events(execute_submit_pr(ops, tmp_path, "test-session"))

    assert isinstance(result, SubmitPRResult)
    assert result.success is True
    assert result.pr_number == 42
    assert result.pr_url == "https://github.com/org/repo/pull/42"
    assert result.pr_title == "feat: Add new widget component"
    assert result.branch_name == "feature-widget"
    assert "PR #42 submitted successfully" in result.message

    # Verify Claude was called
    assert claude.call_count == 1
    call = claude.generate_commit_message_calls[0]
    assert call.current_branch == "feature-widget"
    assert call.parent_branch == "main"


def test_submit_pr_with_force_flag(tmp_path: Path) -> None:
    """Test that force flag is passed through to submit_stack."""
    claude = FakeClaudeExecutor(title="Fix bug", body="Fixes the issue")
    ops = (
        FakeGtKitOps(claude_executor=claude)
        .with_repo_root(str(tmp_path))
        .with_branch("fix-bug", parent="main")
        .with_commits(1)
        .with_pr(99, url="https://github.com/org/repo/pull/99")
    )

    result = render_events(execute_submit_pr(ops, tmp_path, "test-session", force=True))

    assert isinstance(result, SubmitPRResult)
    assert result.success is True
    # The force flag is threaded through - we verify success since FakeGraphite
    # would fail if force wasn't handled properly


def test_submit_pr_preflight_error_gt_not_authenticated(tmp_path: Path) -> None:
    """Test error propagation when Graphite is not authenticated."""
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
        .with_gt_unauthenticated()
    )

    result = render_events(execute_submit_pr(ops, tmp_path, "test-session"))

    assert isinstance(result, SubmitPRError)
    assert result.success is False
    assert result.error_type == "preflight_failed"
    assert "Graphite CLI (gt) is not authenticated" in result.message
    assert result.details["original_error_type"] == "gt_not_authenticated"


def test_submit_pr_preflight_error_gh_not_authenticated(tmp_path: Path) -> None:
    """Test error propagation when GitHub is not authenticated."""
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
        .with_gh_unauthenticated()
    )

    result = render_events(execute_submit_pr(ops, tmp_path, "test-session"))

    assert isinstance(result, SubmitPRError)
    assert result.success is False
    assert result.error_type == "preflight_failed"
    assert "GitHub CLI (gh) is not authenticated" in result.message
    assert result.details["original_error_type"] == "gh_not_authenticated"


def test_submit_pr_preflight_error_no_commits(tmp_path: Path) -> None:
    """Test error when branch has no commits."""
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(0)
    )

    result = render_events(execute_submit_pr(ops, tmp_path, "test-session"))

    assert isinstance(result, SubmitPRError)
    assert result.success is False
    assert result.error_type == "preflight_failed"
    assert "No commits found" in result.message


def test_submit_pr_preflight_error_submit_failed(tmp_path: Path) -> None:
    """Test error when gt submit fails."""
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
        .with_submit_failure(stderr="Network timeout")
    )

    result = render_events(execute_submit_pr(ops, tmp_path, "test-session"))

    assert isinstance(result, SubmitPRError)
    assert result.success is False
    assert result.error_type == "preflight_failed"


def test_submit_pr_ai_generation_error(tmp_path: Path) -> None:
    """Test error when AI generation fails."""
    claude = FakeClaudeExecutor(should_raise=RuntimeError("Claude API unavailable"))
    ops = (
        FakeGtKitOps(claude_executor=claude)
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
        .with_pr(123, url="https://github.com/org/repo/pull/123")
    )

    result = render_events(execute_submit_pr(ops, tmp_path, "test-session"))

    assert isinstance(result, SubmitPRError)
    assert result.success is False
    assert result.error_type == "ai_generation_failed"
    assert "AI generation failed" in result.message
    assert "Claude API unavailable" in result.details["exception"]


def test_submit_pr_finalize_error(tmp_path: Path) -> None:
    """Test error when finalize phase fails."""
    claude = FakeClaudeExecutor(title="Test", body="Body")
    ops = (
        FakeGtKitOps(claude_executor=claude)
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
        .with_pr(123, url="https://github.com/org/repo/pull/123")
        .with_pr_update_failure()
    )

    result = render_events(execute_submit_pr(ops, tmp_path, "test-session"))

    assert isinstance(result, SubmitPRError)
    assert result.success is False
    assert result.error_type == "finalize_failed"


def test_submit_pr_multiple_commits_squashed(tmp_path: Path) -> None:
    """Test that multiple commits are squashed before submission."""
    claude = FakeClaudeExecutor(title="Squashed commit", body="All commits combined")
    ops = (
        FakeGtKitOps(claude_executor=claude)
        .with_repo_root(str(tmp_path))
        .with_branch("feature-multi", parent="main")
        .with_commits(5)  # Multiple commits
        .with_pr(77, url="https://github.com/org/repo/pull/77")
    )

    result = render_events(execute_submit_pr(ops, tmp_path, "test-session"))

    assert isinstance(result, SubmitPRResult)
    assert result.success is True
    assert result.pr_number == 77


def test_submit_pr_with_issue_reference(tmp_path: Path) -> None:
    """Test that issue reference is included in result."""
    # Create .impl/issue.json
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    issue_json = impl_dir / "issue.json"
    issue_json.write_text(
        '{"issue_number": 456, "issue_url": "https://github.com/repo/issues/456", '
        '"created_at": "2025-01-01T00:00:00Z", "synced_at": "2025-01-01T00:00:00Z"}',
        encoding="utf-8",
    )

    claude = FakeClaudeExecutor(title="Fix issue", body="Resolves the bug")
    ops = (
        FakeGtKitOps(claude_executor=claude)
        .with_repo_root(str(tmp_path))
        .with_branch("fix-issue-456", parent="main")
        .with_commits(1)
        .with_pr(789, url="https://github.com/org/repo/pull/789")
    )

    result = render_events(execute_submit_pr(ops, tmp_path, "test-session"))

    assert isinstance(result, SubmitPRResult)
    assert result.success is True
    assert result.issue_number == 456


def test_submit_pr_squash_conflict_error(tmp_path: Path) -> None:
    """Test error when squash has conflicts."""
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(3)
        .with_squash_conflict()
    )

    result = render_events(execute_submit_pr(ops, tmp_path, "test-session"))

    assert isinstance(result, SubmitPRError)
    assert result.success is False
    assert result.error_type == "preflight_failed"
    assert "squash_conflict" in result.details.get("original_error_type", "")


def test_submit_pr_empty_parent_branch_error(tmp_path: Path) -> None:
    """Test error when parent branch has no changes (already merged)."""
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
        .with_submit_success_but_nothing_submitted()
    )

    result = render_events(execute_submit_pr(ops, tmp_path, "test-session"))

    assert isinstance(result, SubmitPRError)
    assert result.success is False
    assert result.error_type == "preflight_failed"
    assert "submit_empty_parent" in result.details.get("original_error_type", "")
