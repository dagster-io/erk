"""Tests for pr_prep kit CLI command using fake ops."""

from pathlib import Path

from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.prep import execute_prep
from erk_shared.integrations.gt.types import PrepError, PrepResult

from tests.unit.kits.gt.fake_ops import FakeGtKitOps


class TestPrepExecution:
    """Tests for prep phase execution logic."""

    def test_prep_gt_not_authenticated(self, tmp_path: Path) -> None:
        """Test error when Graphite CLI is not authenticated."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_gt_unauthenticated()
        )

        result = render_events(execute_prep(ops, tmp_path, "test-session"))

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "gt_not_authenticated"
        assert "Graphite CLI (gt) is not authenticated" in result.message
        assert result.details["fix"] == "Run 'gt auth' to authenticate with Graphite"
        assert result.details["authenticated"] is False

    def test_prep_gh_not_authenticated(self, tmp_path: Path) -> None:
        """Test error when GitHub CLI is not authenticated (gt is authenticated)."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_gh_unauthenticated()
        )

        result = render_events(execute_prep(ops, tmp_path, "test-session"))

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "gh_not_authenticated"
        assert "GitHub CLI (gh) is not authenticated" in result.message
        assert result.details["fix"] == "Run 'gh auth login' to authenticate with GitHub"
        assert result.details["authenticated"] is False

    def test_prep_gt_checked_before_gh(self, tmp_path: Path) -> None:
        """Test that Graphite authentication is checked before GitHub."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_gt_unauthenticated()
            .with_gh_unauthenticated()
        )

        result = render_events(execute_prep(ops, tmp_path, "test-session"))

        # When both are unauthenticated, gt should be reported first
        assert isinstance(result, PrepError)
        assert result.error_type == "gt_not_authenticated"

    def test_prep_no_branch(self, tmp_path: Path) -> None:
        """Test error when current branch cannot be determined."""
        ops = FakeGtKitOps().with_repo_root(str(tmp_path)).with_no_branch()

        result = render_events(execute_prep(ops, tmp_path, "test-session"))

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "no_branch"
        assert "Could not determine current branch" in result.message

    def test_prep_no_parent_branch(self, tmp_path: Path) -> None:
        """Test error when parent branch cannot be determined."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_orphan_branch("orphan-branch")
            .with_commits(1)
        )

        result = render_events(execute_prep(ops, tmp_path, "test-session"))

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "no_parent"
        assert "Could not determine parent branch" in result.message
        assert result.details["branch_name"] == "orphan-branch"

    def test_prep_no_commits(self, tmp_path: Path) -> None:
        """Test error when branch has no commits."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("empty-branch", parent="main")
            .with_commits(0)
        )

        result = render_events(execute_prep(ops, tmp_path, "test-session"))

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "no_commits"
        assert "No commits found in branch" in result.message
        assert result.details["branch_name"] == "empty-branch"
        assert result.details["parent_branch"] == "main"

    def test_prep_single_commit_no_squash(self, tmp_path: Path) -> None:
        """Test prep with single commit (no squash needed)."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
        )

        result = render_events(execute_prep(ops, tmp_path, "test-session"))

        assert isinstance(result, PrepResult)
        assert result.success is True
        assert result.current_branch == "feature-branch"
        assert result.parent_branch == "main"
        assert result.commit_count == 1
        assert result.squashed is False
        assert "Single commit, no squash needed" in result.message

    def test_prep_multiple_commits_squash(self, tmp_path: Path) -> None:
        """Test prep with multiple commits (should squash)."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(3)
        )

        result = render_events(execute_prep(ops, tmp_path, "test-session"))

        assert isinstance(result, PrepResult)
        assert result.success is True
        assert result.current_branch == "feature-branch"
        assert result.parent_branch == "main"
        assert result.commit_count == 3
        assert result.squashed is True
        assert "Squashed 3 commits into 1" in result.message

    def test_prep_restack_conflict_detected(self, tmp_path: Path) -> None:
        """Test error when restack conflicts are detected."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_restack_conflict()
        )

        result = render_events(execute_prep(ops, tmp_path, "test-session"))

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "restack_conflict"
        assert "Restack conflicts detected" in result.message
        assert "Run 'gt restack' to resolve conflicts first" in result.message

    def test_prep_squash_conflict_detected(self, tmp_path: Path) -> None:
        """Test error when squash conflicts are detected."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(3)
            .with_squash_conflict()
        )

        result = render_events(execute_prep(ops, tmp_path, "test-session"))

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "squash_conflict"
        assert "Merge conflicts detected while squashing commits" in result.message

    def test_prep_writes_diff_to_scratch(self, tmp_path: Path) -> None:
        """Test that prep writes diff to scratch file."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
        )

        result = render_events(execute_prep(ops, tmp_path, "test-session"))

        assert isinstance(result, PrepResult)
        assert result.success is True
        # Verify the diff file was created in scratch directory
        diff_path = Path(result.diff_file)
        assert diff_path.exists()
        assert diff_path.parent == tmp_path / ".erk" / "scratch" / "sessions" / "test-session"
        assert diff_path.name.startswith("pr-prep-diff-")
        assert diff_path.name.endswith(".diff")
        # Verify diff content was written
        diff_content = diff_path.read_text()
        assert "diff --git" in diff_content

    def test_prep_success_with_repo_metadata(self, tmp_path: Path) -> None:
        """Test that prep returns correct repo metadata."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(2)
        )

        result = render_events(execute_prep(ops, tmp_path, "test-session"))

        assert isinstance(result, PrepResult)
        assert result.success is True
        assert result.repo_root == str(tmp_path)
        assert result.current_branch == "feature-branch"
        assert result.parent_branch == "main"
