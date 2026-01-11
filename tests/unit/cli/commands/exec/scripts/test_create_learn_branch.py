"""Unit tests for create_learn_branch kit CLI command.

Tests branch creation for learn documentation workflow.
Uses FakeGit for fast, reliable testing without subprocess calls.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.create_learn_branch import (
    create_learn_branch,
)
from erk_shared.context import ErkContext
from erk_shared.git.fake import FakeGit
from erk_shared.github.issues import FakeGitHubIssues

# ============================================================================
# Success Cases (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_create_learn_branch_success(tmp_path: Path) -> None:
    """Test successful branch creation."""
    fake_git = FakeGit(
        trunk_branches={tmp_path: "master"},
        local_branches={tmp_path: ["master", "main"]},
    )
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        fake_git = FakeGit(
            trunk_branches={cwd: "master"},
            local_branches={cwd: ["master", "main"]},
        )

        result = runner.invoke(
            create_learn_branch,
            ["--issue-number", "123", "--trunk-branch", "master"],
            obj=ErkContext.for_test(github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["branch_name"] == "learn-docs-P123"
    assert output["issue_number"] == 123

    # Verify git operations occurred
    assert len(fake_git.checked_out_branches) >= 1
    assert len(fake_git.created_branches) == 1
    assert fake_git.created_branches[0][1] == "learn-docs-P123"
    assert len(fake_git.pushed_branches) == 1


def test_create_learn_branch_with_main(tmp_path: Path) -> None:
    """Test branch creation with main as trunk branch."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        fake_git = FakeGit(
            trunk_branches={cwd: "main"},
            local_branches={cwd: ["main"]},
        )
        fake_gh = FakeGitHubIssues()

        result = runner.invoke(
            create_learn_branch,
            ["--issue-number", "456", "--trunk-branch", "main"],
            obj=ErkContext.for_test(github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["branch_name"] == "learn-docs-P456"


# ============================================================================
# Error Cases (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_create_learn_branch_already_exists(tmp_path: Path) -> None:
    """Test error when branch already exists locally."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        fake_git = FakeGit(
            trunk_branches={cwd: "master"},
            local_branches={cwd: ["master", "learn-docs-P123"]},  # Already exists
        )
        fake_gh = FakeGitHubIssues()

        result = runner.invoke(
            create_learn_branch,
            ["--issue-number", "123", "--trunk-branch", "master"],
            obj=ErkContext.for_test(github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "already exists locally" in output["error"]


def test_create_learn_branch_checkout_fails(tmp_path: Path) -> None:
    """Test error when checkout of trunk branch fails."""

    class FailingCheckoutGit(FakeGit):
        def checkout_branch(self, cwd: Path, branch: str) -> None:
            raise RuntimeError("Failed to checkout branch")

    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        fake_git = FailingCheckoutGit(
            trunk_branches={cwd: "master"},
            local_branches={cwd: ["master"]},
        )
        fake_gh = FakeGitHubIssues()

        result = runner.invoke(
            create_learn_branch,
            ["--issue-number", "789", "--trunk-branch", "master"],
            obj=ErkContext.for_test(github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Failed to checkout" in output["error"]


def test_create_learn_branch_pull_fails(tmp_path: Path) -> None:
    """Test error when pull of trunk branch fails."""

    class FailingPullGit(FakeGit):
        def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
            raise RuntimeError("Network error: could not fetch")

    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        fake_git = FailingPullGit(
            trunk_branches={cwd: "master"},
            local_branches={cwd: ["master"]},
        )
        fake_gh = FakeGitHubIssues()

        result = runner.invoke(
            create_learn_branch,
            ["--issue-number", "101", "--trunk-branch", "master"],
            obj=ErkContext.for_test(github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Failed to pull" in output["error"]


def test_create_learn_branch_create_fails(tmp_path: Path) -> None:
    """Test error when branch creation fails."""

    class FailingCreateGit(FakeGit):
        def create_branch(self, cwd: Path, branch_name: str, start_point: str) -> None:
            raise RuntimeError("Branch creation failed")

    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        fake_git = FailingCreateGit(
            trunk_branches={cwd: "master"},
            local_branches={cwd: ["master"]},
        )
        fake_gh = FakeGitHubIssues()

        result = runner.invoke(
            create_learn_branch,
            ["--issue-number", "202", "--trunk-branch", "master"],
            obj=ErkContext.for_test(github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Failed to create branch" in output["error"]


def test_create_learn_branch_push_fails(tmp_path: Path) -> None:
    """Test error when push fails."""

    class FailingPushGit(FakeGit):
        def push_to_remote(
            self,
            cwd: Path,
            remote: str,
            branch: str,
            *,
            set_upstream: bool = False,
            force: bool = False,
        ) -> None:
            raise RuntimeError("Remote rejected push")

    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        fake_git = FailingPushGit(
            trunk_branches={cwd: "master"},
            local_branches={cwd: ["master"]},
        )
        fake_gh = FakeGitHubIssues()

        result = runner.invoke(
            create_learn_branch,
            ["--issue-number", "303", "--trunk-branch", "master"],
            obj=ErkContext.for_test(github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Failed to push" in output["error"]


# ============================================================================
# JSON Output Structure Tests
# ============================================================================


def test_json_output_structure_success(tmp_path: Path) -> None:
    """Test JSON output structure on success."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        fake_git = FakeGit(
            trunk_branches={cwd: "master"},
            local_branches={cwd: ["master"]},
        )
        fake_gh = FakeGitHubIssues()

        result = runner.invoke(
            create_learn_branch,
            ["--issue-number", "404", "--trunk-branch", "master"],
            obj=ErkContext.for_test(github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify required keys
    assert "success" in output
    assert "branch_name" in output
    assert "issue_number" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["branch_name"], str)
    assert isinstance(output["issue_number"], int)

    # Verify values
    assert output["success"] is True
    assert output["branch_name"] == "learn-docs-P404"
    assert output["issue_number"] == 404


def test_json_output_structure_error(tmp_path: Path) -> None:
    """Test JSON output structure on error."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        fake_git = FakeGit(
            trunk_branches={cwd: "master"},
            local_branches={cwd: ["master", "learn-docs-P505"]},
        )
        fake_gh = FakeGitHubIssues()

        result = runner.invoke(
            create_learn_branch,
            ["--issue-number", "505", "--trunk-branch", "master"],
            obj=ErkContext.for_test(github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)

    # Verify required keys for error
    assert "success" in output
    assert "error" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["error"], str)
    assert output["success"] is False


# ============================================================================
# Git Operation Verification Tests
# ============================================================================


def test_git_operations_sequence(tmp_path: Path) -> None:
    """Test that git operations happen in correct sequence."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        fake_git = FakeGit(
            trunk_branches={cwd: "master"},
            local_branches={cwd: ["master"]},
        )
        fake_gh = FakeGitHubIssues()

        result = runner.invoke(
            create_learn_branch,
            ["--issue-number", "606", "--trunk-branch", "master"],
            obj=ErkContext.for_test(github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0

    # Verify checkout to trunk happened
    trunk_checkouts = [b for _, b in fake_git.checked_out_branches if b == "master"]
    assert len(trunk_checkouts) >= 1

    # Verify pull happened
    assert len(fake_git.pulled_branches) == 1
    assert fake_git.pulled_branches[0][1] == "master"
    assert fake_git.pulled_branches[0][2] is True  # ff_only=True

    # Verify branch was created from trunk
    assert len(fake_git.created_branches) == 1
    _, branch_name, start_point = fake_git.created_branches[0]
    assert branch_name == "learn-docs-P606"
    assert start_point == "master"

    # Verify push with upstream tracking
    assert len(fake_git.pushed_branches) == 1
    remote, branch, set_upstream, force = fake_git.pushed_branches[0]
    assert remote == "origin"
    assert branch == "learn-docs-P606"
    assert set_upstream is True
    assert force is False
