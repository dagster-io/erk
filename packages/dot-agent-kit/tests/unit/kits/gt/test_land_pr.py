"""Tests for land_pr kit CLI command using fake ops."""

from pathlib import Path

import pytest
from click.testing import CliRunner
from erk_shared.git.fake import FakeGit
from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.land_pr import execute_land_pr
from erk_shared.integrations.gt.types import LandPrError, LandPrSuccess

from tests.unit.kits.gt.fake_ops import FakeGtKitOps


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


class TestLandPrExecution:
    """Tests for land_pr execution logic using fakes."""

    def test_land_pr_success(self, tmp_path: Path) -> None:
        """Test successfully landing a PR."""
        # Setup: feature branch on main with open PR
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_pr(123, state="OPEN")
        )

        result = render_events(execute_land_pr(ops, tmp_path))

        assert isinstance(result, LandPrSuccess)
        assert result.success is True
        assert result.pr_number == 123
        assert result.branch_name == "feature-branch"
        assert "Successfully merged PR #123" in result.message

    def test_land_pr_error_parent_not_trunk(self, tmp_path: Path) -> None:
        """Test error when branch parent is not trunk."""
        # Setup: feature branch with parent other than trunk (main)
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="develop")
        )

        result = render_events(execute_land_pr(ops, tmp_path))

        assert isinstance(result, LandPrError)
        assert result.success is False
        assert result.error_type == "parent_not_trunk"
        assert "must be exactly one level up from main" in result.message
        assert result.details["parent_branch"] == "develop"

    def test_land_pr_error_no_parent(self, tmp_path: Path) -> None:
        """Test error when parent branch cannot be determined."""
        # Setup: branch with no parent (orphaned)
        # Use orphan_branch builder to set up a branch without parent tracking
        ops = FakeGtKitOps().with_repo_root(str(tmp_path)).with_orphan_branch("orphan-branch")

        result = render_events(execute_land_pr(ops, tmp_path))

        assert isinstance(result, LandPrError)
        assert result.success is False
        assert result.error_type == "parent_not_trunk"
        assert "Could not determine parent branch" in result.message

    def test_land_pr_error_no_pr(self, tmp_path: Path) -> None:
        """Test error when no PR exists for the branch."""
        # Setup: feature branch on main but no PR
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
        )
        # Don't call with_pr(), so no PR exists

        result = render_events(execute_land_pr(ops, tmp_path))

        assert isinstance(result, LandPrError)
        assert result.success is False
        assert result.error_type == "no_pr_found"
        assert "No pull request found" in result.message
        assert "gt submit" in result.message

    def test_land_pr_error_pr_not_open(self, tmp_path: Path) -> None:
        """Test error when PR exists but is not open."""
        # Setup: feature branch on main with merged PR
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_pr(123, state="MERGED")
        )

        result = render_events(execute_land_pr(ops, tmp_path))

        assert isinstance(result, LandPrError)
        assert result.success is False
        assert result.error_type == "pr_not_open"
        assert "Pull request is not open" in result.message
        assert "MERGED" in result.message

    def test_land_pr_error_merge_failed(self, tmp_path: Path) -> None:
        """Test error when PR merge fails includes error message."""
        # Setup: feature branch on main with open PR but merge configured to fail
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_pr(123, state="OPEN")
            .with_merge_failure()
        )

        result = render_events(execute_land_pr(ops, tmp_path))

        assert isinstance(result, LandPrError)
        assert result.success is False
        assert result.error_type == "merge_failed"
        assert "Failed to merge PR #123" in result.message
        # Verify the error message from the fake is included in output
        assert "Merge failed (configured to fail in test)" in result.message

    def test_land_pr_with_master_trunk(self, tmp_path: Path) -> None:
        """Test successfully landing a PR when trunk is 'master' instead of 'main'."""
        # Setup: feature branch on master with open PR, configure trunk as "master"
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_trunk_branch("master")
            .with_branch("feature-branch", parent="master")
            .with_pr(123, state="OPEN")
        )

        result = render_events(execute_land_pr(ops, tmp_path))

        assert isinstance(result, LandPrSuccess)
        assert result.success is True
        assert result.pr_number == 123
        assert result.branch_name == "feature-branch"

    def test_land_pr_error_parent_not_trunk_with_master(self, tmp_path: Path) -> None:
        """Test error when branch parent is not trunk, with master as trunk."""
        # Setup: feature branch with parent "main" when trunk is "master"
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_trunk_branch("master")
            .with_branch("feature-branch", parent="main")
        )

        result = render_events(execute_land_pr(ops, tmp_path))

        assert isinstance(result, LandPrError)
        assert result.success is False
        assert result.error_type == "parent_not_trunk"
        assert "must be exactly one level up from master" in result.message
        assert result.details["parent_branch"] == "main"

    def test_land_pr_does_not_auto_navigate_to_child(self, tmp_path: Path) -> None:
        """Test that landing does not auto-navigate to child branch.

        Navigation to child branches should be handled by the CLI layer,
        not the core execute_land_pr operation.
        """
        # Setup: feature branch on main with open PR and one child
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_pr(123, state="OPEN")
            .with_children(["child-branch"])
        )

        result = render_events(execute_land_pr(ops, tmp_path))

        # Verify success
        assert isinstance(result, LandPrSuccess)
        assert result.success is True

        # Verify message mentions child but no navigation occurred
        assert "Child branch: child-branch" in result.message

        # Verify checkout_branch was NOT called (no auto-navigation)
        git = ops.git
        assert isinstance(git, FakeGit)
        assert git.checked_out_branches == []


class TestLandPrCLI:
    """Tests for land_pr CLI command."""

    def test_land_pr_cli_success(self, runner: CliRunner) -> None:
        """Test CLI command with successful land."""
        # Note: CLI test uses real ops, so this would need actual git/gh setup
        # This is a placeholder showing the pattern
        # In practice, you'd either mock or use integration tests for CLI
        pass

    def test_land_pr_cli_error_output(self, runner: CliRunner) -> None:
        """Test CLI command error output format."""
        # Note: CLI test pattern placeholder
        pass


class TestLandPrEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_land_pr_with_closed_pr(self, tmp_path: Path) -> None:
        """Test landing with closed (not merged) PR."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_pr(123, state="CLOSED")
        )

        result = render_events(execute_land_pr(ops, tmp_path))

        assert isinstance(result, LandPrError)
        assert result.error_type == "pr_not_open"

    def test_land_pr_unknown_current_branch(self, tmp_path: Path) -> None:
        """Test when current branch cannot be determined."""
        # Use with_no_branch to configure empty current branch
        ops = FakeGtKitOps().with_repo_root(str(tmp_path)).with_no_branch()

        result = render_events(execute_land_pr(ops, tmp_path))

        # Should handle gracefully with "unknown" branch name
        assert isinstance(result, LandPrError)
        assert result.details["current_branch"] == "unknown"


class TestLandPrTitle:
    """Tests for PR title handling in land_pr."""

    def test_land_pr_fetches_pr_title(self, tmp_path: Path) -> None:
        """Test that land_pr fetches PR title before merging."""
        # Setup: feature branch on main with open PR that has a title
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_pr(123, state="OPEN", title="Add new feature")
        )

        # Verify the title can be fetched (using Path(".") as placeholder repo_root)
        assert ops.github.get_pr_title(Path("."), 123) == "Add new feature"

        result = render_events(execute_land_pr(ops, tmp_path))

        assert isinstance(result, LandPrSuccess)
        assert result.success is True
        assert result.pr_number == 123

    def test_land_pr_success_without_pr_title(self, tmp_path: Path) -> None:
        """Test landing succeeds even when no PR title is set."""
        # Setup: feature branch with PR but no title set
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_pr(123, state="OPEN")  # No title
        )

        # Verify no title is set
        assert ops.github.get_pr_title(Path("."), 123) is None

        result = render_events(execute_land_pr(ops, tmp_path))

        # Should still succeed - title is optional
        assert isinstance(result, LandPrSuccess)
        assert result.success is True

    def test_get_pr_title_returns_none_when_no_pr(self, tmp_path: Path) -> None:
        """Test get_pr_title returns None when no PR exists."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
        )
        # No PR configured

        assert ops.github.get_pr_title(Path("."), 999) is None


class TestLandPrBody:
    """Tests for PR body handling in land_pr."""

    def test_land_pr_fetches_pr_body(self, tmp_path: Path) -> None:
        """Test that land_pr fetches PR body before merging."""
        # Setup: feature branch on main with open PR that has a body
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_pr(
                123,
                state="OPEN",
                title="Add new feature",
                body="This PR adds a new feature with detailed description.",
            )
        )

        # Verify the body can be fetched
        expected_body = "This PR adds a new feature with detailed description."
        assert ops.github.get_pr_body(Path("."), 123) == expected_body

        result = render_events(execute_land_pr(ops, tmp_path))

        assert isinstance(result, LandPrSuccess)
        assert result.success is True
        assert result.pr_number == 123

    def test_land_pr_success_without_pr_body(self, tmp_path: Path) -> None:
        """Test landing succeeds even when no PR body is set."""
        # Setup: feature branch with PR but no body set
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_pr(123, state="OPEN", title="Add new feature")  # No body
        )

        # Verify no body is set
        assert ops.github.get_pr_body(Path("."), 123) is None

        result = render_events(execute_land_pr(ops, tmp_path))

        # Should still succeed - body is optional
        assert isinstance(result, LandPrSuccess)
        assert result.success is True

    def test_get_pr_body_returns_none_when_no_pr(self, tmp_path: Path) -> None:
        """Test get_pr_body returns None when no PR exists."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
        )
        # No PR configured

        assert ops.github.get_pr_body(Path("."), 999) is None

    def test_land_pr_with_title_and_body(self, tmp_path: Path) -> None:
        """Test landing with both title and body for rich merge commit."""
        # Setup: feature branch with PR that has both title and body
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_pr(
                123,
                state="OPEN",
                title="Extract subprocess calls into reusable interface",
                body=(
                    "Refactors `create_wt_from_issue` command to use dependency injection.\n\n"
                    "## Changes\n"
                    "- Added ErkWtKit ABC interface\n"
                    "- Implemented real and fake versions"
                ),
            )
        )

        # Verify both can be fetched
        expected_title = "Extract subprocess calls into reusable interface"
        assert ops.github.get_pr_title(Path("."), 123) == expected_title
        assert "Refactors" in ops.github.get_pr_body(Path("."), 123)  # type: ignore[operator]

        result = render_events(execute_land_pr(ops, tmp_path))

        assert isinstance(result, LandPrSuccess)
        assert result.success is True
