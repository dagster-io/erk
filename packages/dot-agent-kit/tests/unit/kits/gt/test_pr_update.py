"""Tests for update_pr kit CLI command using fake ops."""

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from erk_shared.integrations.gt.kit_cli_commands.gt.pr_update import (
    execute_update_pr,
    pr_update,
)

from tests.unit.kits.gt.fake_ops import FakeGtKitOps


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


class TestExecuteUpdatePr:
    """Tests for execute_update_pr function."""

    def test_update_pr_success_with_uncommitted_changes(self) -> None:
        """Test successful update with uncommitted changes."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_uncommitted_files(["file.txt"])
            .with_commits(1)
            .with_pr(123, url="https://github.com/repo/pull/123")
        )

        result = execute_update_pr(ops)

        assert result["success"] is True
        assert result["pr_number"] == 123
        assert result["pr_url"] == "https://github.com/repo/pull/123"

    def test_update_pr_success_without_uncommitted_changes(self) -> None:
        """Test successful update without uncommitted changes."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123, url="https://github.com/repo/pull/123")
        )

        result = execute_update_pr(ops)

        assert result["success"] is True
        assert result["pr_number"] == 123

    def test_update_pr_restack_fails_generic(self) -> None:
        """Test error when restack fails with generic error."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_restack_failure(stdout="", stderr="Failed to rebase")
        )

        result = execute_update_pr(ops)

        assert result["success"] is False
        assert result["error_type"] == "restack_failed"
        assert "Failed to restack branch" in result["error"]
        assert "stderr" in result["details"]

    def test_update_pr_restack_conflict_detected_via_stderr(self) -> None:
        """Test that restack conflicts are detected via stderr pattern matching."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_restack_failure(
                stdout="",
                stderr=(
                    "error: could not apply abc123... commit message\n"
                    "CONFLICT (content): Merge conflict in file.txt"
                ),
            )
        )

        result = execute_update_pr(ops)

        assert result["success"] is False
        assert result["error_type"] == "restack_conflict"
        assert "Merge conflict detected during restack" in result["error"]
        assert "gt restack --continue" in result["error"]
        assert "CONFLICT" in result["details"]["stderr"]

    def test_update_pr_restack_conflict_detected_via_stdout(self) -> None:
        """Test that restack conflicts are detected via stdout pattern matching."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_restack_failure(
                stdout="Merge conflict in src/main.py",
                stderr="",
            )
        )

        result = execute_update_pr(ops)

        assert result["success"] is False
        assert result["error_type"] == "restack_conflict"
        assert "Merge conflict detected during restack" in result["error"]

    def test_update_pr_restack_conflict_case_insensitive(self) -> None:
        """Test that conflict detection is case insensitive."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_restack_failure(
                stdout="",
                stderr="CONFLICT detected in file.txt",
            )
        )

        result = execute_update_pr(ops)

        assert result["success"] is False
        assert result["error_type"] == "restack_conflict"

    def test_update_pr_submit_fails(self) -> None:
        """Test error when submit fails."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_submit_failure(stderr="network error")
        )

        result = execute_update_pr(ops)

        assert result["success"] is False
        assert "Failed to submit update" in result["error"]

    def test_update_pr_remote_divergence_detected(self) -> None:
        """Test that remote divergence is detected and returns hard abort message."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_submit_failure(
                stderr="ERROR: Branch feature-branch has been updated remotely. "
                "Use gt get or gt sync to sync with remote before submitting"
            )
        )

        result = execute_update_pr(ops)

        assert result["success"] is False
        assert result["error_type"] == "remote_divergence"
        assert "ABORT" in result["error"]
        assert "Do NOT auto-sync" in result["error"]

    def test_update_pr_add_fails(self) -> None:
        """Test error when git add fails."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_uncommitted_files(["file.txt"])
            .with_add_failure()
        )

        result = execute_update_pr(ops)

        assert result["success"] is False
        assert "Failed to stage changes" in result["error"]


class TestPrUpdateCLI:
    """Tests for pr_update CLI command."""

    def test_pr_update_cli_success(self, runner: CliRunner) -> None:
        """Test CLI command with successful execution."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123, url="https://github.com/repo/pull/123")
        )

        with patch(
            "erk_shared.integrations.gt.kit_cli_commands.gt.pr_update.RealGtKit",
            return_value=ops,
        ):
            result = runner.invoke(pr_update)

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["pr_number"] == 123

    def test_pr_update_cli_failure_exit_code(self, runner: CliRunner) -> None:
        """Test CLI command returns non-zero exit code on failure."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_restack_failure(stderr="failed")
        )

        with patch(
            "erk_shared.integrations.gt.kit_cli_commands.gt.pr_update.RealGtKit",
            return_value=ops,
        ):
            result = runner.invoke(pr_update)

        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["success"] is False
