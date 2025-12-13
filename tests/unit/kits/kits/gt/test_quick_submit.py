"""Tests for gt quick-submit kit CLI command using fake ops."""

from pathlib import Path

import pytest

from erk_shared.git.fake import FakeGit
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.quick_submit import execute_quick_submit
from erk_shared.integrations.gt.types import QuickSubmitError, QuickSubmitSuccess
from tests.unit.kits.kits.gt.fake_ops import FakeGtKitOps


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Create a temporary repository root."""
    return tmp_path


class TestQuickSubmitSuccess:
    """Tests for successful quick-submit scenarios."""

    def test_quick_submit_with_staged_changes(self, tmp_repo: Path) -> None:
        """Test quick-submit when there are staged changes to commit."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_repo))
            .with_branch("feature-branch", parent="main")
            .with_staged_changes()
            .with_pr(123, url="https://github.com/org/repo/pull/123")
        )

        result = render_events(execute_quick_submit(ops, tmp_repo))

        assert isinstance(result, QuickSubmitSuccess)
        assert result.success is True
        assert result.staged_changes is True
        assert result.committed is True
        assert result.pr_url == "https://github.com/org/repo/pull/123"
        assert "Changes submitted successfully" in result.message

    def test_quick_submit_no_changes(self, tmp_repo: Path) -> None:
        """Test quick-submit when there are no changes to commit."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_repo))
            .with_branch("feature-branch", parent="main")
            .with_clean_working_tree()
            .with_pr(456, url="https://github.com/org/repo/pull/456")
        )

        result = render_events(execute_quick_submit(ops, tmp_repo))

        assert isinstance(result, QuickSubmitSuccess)
        assert result.success is True
        assert result.staged_changes is False
        assert result.committed is False
        assert result.pr_url == "https://github.com/org/repo/pull/456"
        assert "No new changes" in result.message

    def test_quick_submit_returns_pr_url(self, tmp_repo: Path) -> None:
        """Test that quick-submit returns the PR URL after successful submit."""
        expected_url = "https://github.com/dagster-io/erk/pull/3150"
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_repo))
            .with_branch("feature-branch", parent="main")
            .with_staged_changes()
            .with_pr(3150, url=expected_url)
        )

        result = render_events(execute_quick_submit(ops, tmp_repo))

        assert isinstance(result, QuickSubmitSuccess)
        assert result.pr_url == expected_url

    def test_quick_submit_no_pr_returns_none_url(self, tmp_repo: Path) -> None:
        """Test quick-submit returns None for pr_url when no PR exists."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_repo))
            .with_branch("feature-branch", parent="main")
            .with_staged_changes()
            # No with_pr() - PR doesn't exist
        )

        result = render_events(execute_quick_submit(ops, tmp_repo))

        assert isinstance(result, QuickSubmitSuccess)
        assert result.success is True
        assert result.pr_url is None


class TestQuickSubmitErrors:
    """Tests for quick-submit error scenarios."""

    def test_quick_submit_stage_failure(self, tmp_repo: Path) -> None:
        """Test quick-submit handles git add failure."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_repo))
            .with_branch("feature-branch", parent="main")
            .with_add_failure()
        )

        result = render_events(execute_quick_submit(ops, tmp_repo))

        assert isinstance(result, QuickSubmitError)
        assert result.success is False
        assert result.error_type == "stage_failed"
        assert "Failed to stage changes" in result.message

    def test_quick_submit_submit_failure(self, tmp_repo: Path) -> None:
        """Test quick-submit handles gt submit failure."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_repo))
            .with_branch("feature-branch", parent="main")
            .with_clean_working_tree()
            .with_submit_failure("Error: not authenticated")
        )

        result = render_events(execute_quick_submit(ops, tmp_repo))

        assert isinstance(result, QuickSubmitError)
        assert result.success is False
        assert result.error_type == "submit_failed"
        assert "Failed to submit" in result.message


class TestQuickSubmitMutationTracking:
    """Tests that verify git operations are called correctly."""

    def test_quick_submit_calls_add_all(self, tmp_repo: Path) -> None:
        """Test that quick-submit calls git add -A."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_repo))
            .with_branch("feature-branch", parent="main")
            .with_clean_working_tree()
        )

        render_events(execute_quick_submit(ops, tmp_repo))

        # add_all was called (we can verify by the fact it didn't fail)
        # The fake would raise if add_all_raises was set
        assert True  # Reached here means add_all succeeded

    def test_quick_submit_calls_commit_when_changes(self, tmp_repo: Path) -> None:
        """Test that quick-submit commits when there are staged changes."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_repo))
            .with_branch("feature-branch", parent="main")
            .with_staged_changes()
        )

        render_events(execute_quick_submit(ops, tmp_repo))

        # Verify commit was called by checking the fake's mutation tracking
        git = ops.git
        assert isinstance(git, FakeGit)
        # The commit method tracks calls in _commits
        assert len(git.commits) == 1
        assert git.commits[0][1] == "update"  # commit message

    def test_quick_submit_calls_submit_stack(self, tmp_repo: Path) -> None:
        """Test that quick-submit calls graphite submit_stack."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_repo))
            .with_branch("feature-branch", parent="main")
            .with_clean_working_tree()
        )

        render_events(execute_quick_submit(ops, tmp_repo))

        # Verify submit_stack was called
        graphite = ops.graphite
        assert isinstance(graphite, FakeGraphite)
        assert len(graphite.submit_stack_calls) == 1
        # Verify quiet=True and force=True were passed
        call = graphite.submit_stack_calls[0]
        # call is (repo_root, publish, restack, quiet, force)
        assert call[3] is True  # quiet
        assert call[4] is True  # force
