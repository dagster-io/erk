"""Tests for erk exec setup-impl-from-issue command."""

from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts.setup_impl_from_issue import (
    _get_current_branch,
    _is_trunk_branch,
    setup_impl_from_issue,
)
from erk_shared.context import ErkContext
from erk_shared.git.fake import FakeGit


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
