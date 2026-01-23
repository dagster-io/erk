"""Tests for erk exec setup-impl-from-issue command."""

import json
from datetime import UTC, datetime
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts.setup_impl_from_issue import (
    _get_current_branch,
    _is_trunk_branch,
    setup_impl_from_issue,
)
from erk_shared.context.context import ErkContext
from erk_shared.context.testing import context_for_test
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.git.fake import FakeGit
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo


class TestGetCurrentBranch:
    """Tests for the _get_current_branch helper function."""

    def test_returns_branch_name(self, tmp_path: Path) -> None:
        """Returns current branch name when on a branch."""
        git = FakeGit(current_branches={tmp_path: "feature-branch"})
        result = _get_current_branch(git, tmp_path)
        assert result == "feature-branch"

    def test_raises_on_detached_head(self, tmp_path: Path) -> None:
        """Raises ClickException when in detached HEAD state."""
        git = FakeGit(current_branches={tmp_path: None})
        with pytest.raises(click.ClickException) as exc_info:
            _get_current_branch(git, tmp_path)
        assert "detached HEAD" in str(exc_info.value)


class TestIsTrunkBranch:
    """Tests for the _is_trunk_branch helper function."""

    def test_main_is_trunk(self) -> None:
        """main is recognized as a trunk branch."""
        assert _is_trunk_branch("main") is True

    def test_master_is_trunk(self) -> None:
        """master is recognized as a trunk branch."""
        assert _is_trunk_branch("master") is True

    def test_feature_branch_is_not_trunk(self) -> None:
        """Feature branches are not trunk branches."""
        assert _is_trunk_branch("feature-branch") is False
        assert _is_trunk_branch("P123-my-feature") is False
        assert _is_trunk_branch("fix/bug-123") is False

    def test_development_is_not_trunk(self) -> None:
        """Common development branches are not trunk."""
        assert _is_trunk_branch("develop") is False
        assert _is_trunk_branch("development") is False


class TestSetupImplFromIssueValidation:
    """Tests for validation in setup-impl-from-issue command."""

    def test_missing_issue_shows_error(self, tmp_path: Path) -> None:
        """Command fails gracefully when issue cannot be found."""
        runner = CliRunner()

        # Create a minimal context
        ctx = ErkContext.for_test(cwd=tmp_path)

        # The command requires a GitHub issue that doesn't exist
        # This test verifies the error handling for missing issues
        result = runner.invoke(
            setup_impl_from_issue,
            ["999999"],  # Non-existent issue number
            obj=ctx,
            catch_exceptions=False,
        )

        # Command should fail with exit code 1
        # (actual behavior depends on whether we're mocking GitHub or not)
        # For this unit test, we're primarily testing the CLI interface
        assert result.exit_code != 0 or "error" in result.output.lower()


class TestSetupImplFromIssueNoImplFlag:
    """Tests for --no-impl flag in setup-impl-from-issue command."""

    def test_no_impl_flag_is_accepted(self, tmp_path: Path) -> None:
        """Verify --no-impl flag is accepted by the CLI.

        Note: Full integration testing of --no-impl behavior requires
        refactoring the command to use DI for GitHubIssues. This test
        just verifies the flag is accepted without syntax errors.
        """
        runner = CliRunner()

        # Create a minimal context
        ctx = ErkContext.for_test(cwd=tmp_path)

        # The command will fail because it can't reach GitHub,
        # but we verify the flag is accepted without a click.UsageError
        result = runner.invoke(
            setup_impl_from_issue,
            ["42", "--no-impl"],
            obj=ctx,
        )

        # Verify no usage error (flag was accepted)
        assert "Usage:" not in result.output, "--no-impl flag should be accepted"
        assert "Error: No such option:" not in result.output, "--no-impl should be a valid option"

        # The command should fail due to GitHub access, not CLI parsing
        # (exit code 1 is expected when GitHub fails)
        assert result.exit_code == 1


class TestSetupImplFromIssueBranchManager:
    """Tests verifying BranchManager is used for branch creation."""

    def test_uses_branch_manager_with_graphite_tracking(self, tmp_path: Path) -> None:
        """Verify command uses BranchManager which enables Graphite tracking.

        When Graphite is enabled (FakeGraphite, not GraphiteDisabled), branch
        creation should go through GraphiteBranchManager which calls
        graphite.track_branch() after creating the git branch.

        This test verifies the behavior change from the PR that switched from
        direct git.create_branch() to branch_manager.create_branch().
        """
        # Arrange: Create plan issue with erk-plan label
        now = datetime.now(UTC)
        plan_issue = IssueInfo(
            number=42,
            title="Test Plan",
            body="# Plan Content\n\nSome plan details here.",
            state="OPEN",
            url="https://github.com/test-owner/test-repo/issues/42",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-author",
        )
        fake_issues = FakeGitHubIssues(issues={42: plan_issue})

        # Configure FakeGit with:
        # - current branch on main
        # - empty list of local branches (so branch doesn't exist)
        fake_git = FakeGit(
            current_branches={tmp_path: "main"},
            local_branches=[],
        )

        # Configure FakeGraphite to track calls
        fake_graphite = FakeGraphite()

        # Create test context with all fakes
        # Use context_for_test directly to pass graphite parameter
        ctx = context_for_test(
            github_issues=fake_issues,
            git=fake_git,
            graphite=fake_graphite,
            cwd=tmp_path,
            repo_root=tmp_path,
        )

        # Act: Invoke command with --no-impl to skip folder creation
        runner = CliRunner()
        result = runner.invoke(
            setup_impl_from_issue,
            ["42", "--no-impl"],
            obj=ctx,
        )

        # Assert: Command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: Verify output contains valid JSON
        # The output may have status messages before the JSON line
        # Extract the JSON line (last non-empty line that starts with '{')
        output_lines = result.output.strip().split("\n")
        json_line = next(line for line in reversed(output_lines) if line.startswith("{"))
        output = json.loads(json_line)
        assert output["success"] is True
        assert output["issue_number"] == 42

        # Assert: Graphite track_branch was called (key assertion)
        # This verifies the branch was created through BranchManager,
        # not direct git calls
        assert len(fake_graphite.track_branch_calls) == 1
        tracked_call = fake_graphite.track_branch_calls[0]
        # track_branch_calls are (cwd, branch_name, parent_branch) tuples
        assert tracked_call[0] == tmp_path  # repo_root
        assert tracked_call[1].startswith("P42-")  # branch_name starts with issue prefix
        assert tracked_call[2] == "main"  # parent_branch is main

    def test_checks_out_newly_created_branch(self, tmp_path: Path) -> None:
        """Verify setup-impl-from-issue checks out the newly created branch.

        This test ensures that after creating a new branch, the command also
        checks it out so that subsequent operations happen on the new branch,
        not the parent branch.

        Previously, only create_branch was called without checkout_branch,
        causing implementation changes to end up on the wrong branch.
        """
        # Arrange: Create plan issue with erk-plan label
        now = datetime.now(UTC)
        plan_issue = IssueInfo(
            number=99,
            title="Branch Checkout Test",
            body="# Plan Content\n\nVerify checkout after branch creation.",
            state="OPEN",
            url="https://github.com/test-owner/test-repo/issues/99",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-author",
        )
        fake_issues = FakeGitHubIssues(issues={99: plan_issue})

        # Configure FakeGit with:
        # - current branch on a feature branch (to test stacking)
        # - empty list of local branches (so new branch doesn't exist)
        fake_git = FakeGit(
            current_branches={tmp_path: "parent-feature"},
            local_branches=[],
        )

        # Configure FakeGraphite to track calls
        fake_graphite = FakeGraphite()

        # Create test context with all fakes
        ctx = context_for_test(
            github_issues=fake_issues,
            git=fake_git,
            graphite=fake_graphite,
            cwd=tmp_path,
            repo_root=tmp_path,
        )

        # Act: Invoke command with --no-impl to skip folder creation
        runner = CliRunner()
        result = runner.invoke(
            setup_impl_from_issue,
            ["99", "--no-impl"],
            obj=ctx,
        )

        # Assert: Command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: Branch was created
        assert len(fake_git.created_branches) == 1
        created_branch = fake_git.created_branches[0]
        branch_name = created_branch[1]  # (cwd, branch_name, start_point)
        assert branch_name.startswith("P99-")

        # Assert: The newly created branch was checked out (KEY ASSERTION)
        # This is the bug fix - previously checkout_branch was never called
        # after GraphiteBranchManager.create_branch, which does temporary checkouts
        # internally but restores the original branch at the end.
        #
        # GraphiteBranchManager.create_branch does:
        #   1. Checkout new branch (to track with Graphite)
        #   2. Restore original branch (parent-feature)
        # Then setup_impl_from_issue should:
        #   3. Checkout the new branch again
        #
        # So we verify the LAST checkout is to the new branch
        assert len(fake_git.checked_out_branches) >= 1, "At least one checkout should occur"
        final_checkout = fake_git.checked_out_branches[-1]
        # checked_out_branches are (cwd, branch) tuples
        assert final_checkout[0] == tmp_path
        assert final_checkout[1] == branch_name  # Last checkout is to the new branch
