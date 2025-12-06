"""Unit tests for add_issue_label kit CLI command.

Tests adding labels to GitHub issues.
Uses FakeGitHubIssues for fast, reliable testing.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.fake import FakeGit
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo

from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.add_issue_label import (
    add_issue_label,
)


def make_issue_info(number: int, labels: list[str] | None = None) -> IssueInfo:
    """Create test IssueInfo with given number and labels."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=f"Test Issue #{number}",
        body="Test issue body",
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=labels or [],
        assignees=[],
        created_at=now,
        updated_at=now,
    )


# ============================================================================
# Success Cases (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_add_label_success(tmp_path: Path) -> None:
    """Test successfully adding a label to an issue."""
    fake_gh = FakeGitHubIssues(
        issues={100: make_issue_info(100)},
        labels={"extraction-failed", "raw-extraction"},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            add_issue_label,
            ["--issue-number", "100", "--label", "extraction-failed"],
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 100
    assert output["label"] == "extraction-failed"


def test_add_label_different_label(tmp_path: Path) -> None:
    """Test adding a different label."""
    fake_gh = FakeGitHubIssues(
        issues={200: make_issue_info(200)},
        labels={"extraction-complete", "raw-extraction"},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            add_issue_label,
            ["--issue-number", "200", "--label", "extraction-complete"],
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["label"] == "extraction-complete"


def test_add_label_issue_already_has_label(tmp_path: Path) -> None:
    """Test adding a label that already exists on the issue (idempotent)."""
    fake_gh = FakeGitHubIssues(
        issues={300: make_issue_info(300, labels=["extraction-failed"])},
        labels={"extraction-failed"},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            add_issue_label,
            ["--issue-number", "300", "--label", "extraction-failed"],
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd
            ),
        )

    # Should succeed - adding existing label is a no-op
    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True


# ============================================================================
# Error Cases (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_add_label_github_api_failure(tmp_path: Path) -> None:
    """Test error when GitHub API fails."""

    class FailingFakeGitHubIssues(FakeGitHubIssues):
        def ensure_label_on_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
            raise RuntimeError("GitHub API rate limit exceeded")

    fake_gh = FailingFakeGitHubIssues(
        issues={400: make_issue_info(400)},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            add_issue_label,
            ["--issue-number", "400", "--label", "extraction-failed"],
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd
            ),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Failed to add label" in output["error"]
    assert "rate limit" in output["error"]


def test_add_label_network_error(tmp_path: Path) -> None:
    """Test error when network fails."""

    class NetworkFailingGitHubIssues(FakeGitHubIssues):
        def ensure_label_on_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
            raise RuntimeError("Network connection timed out")

    fake_gh = NetworkFailingGitHubIssues(
        issues={500: make_issue_info(500)},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            add_issue_label,
            ["--issue-number", "500", "--label", "test-label"],
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd
            ),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Failed to add label" in output["error"]


# ============================================================================
# JSON Output Structure Tests
# ============================================================================


def test_json_output_structure_success(tmp_path: Path) -> None:
    """Test JSON output structure on success."""
    fake_gh = FakeGitHubIssues(
        issues={600: make_issue_info(600)},
        labels={"test-label"},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            add_issue_label,
            ["--issue-number", "600", "--label", "test-label"],
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd
            ),
        )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify required keys
    assert "success" in output
    assert "issue_number" in output
    assert "label" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)
    assert isinstance(output["label"], str)

    # Verify values
    assert output["success"] is True
    assert output["issue_number"] == 600
    assert output["label"] == "test-label"


def test_json_output_structure_error(tmp_path: Path) -> None:
    """Test JSON output structure on error."""

    class FailingFakeGitHubIssues(FakeGitHubIssues):
        def ensure_label_on_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
            raise RuntimeError("Some error")

    fake_gh = FailingFakeGitHubIssues(
        issues={700: make_issue_info(700)},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            add_issue_label,
            ["--issue-number", "700", "--label", "some-label"],
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd
            ),
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
# CLI Argument Tests
# ============================================================================


def test_missing_issue_number(tmp_path: Path) -> None:
    """Test error when issue number is missing."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            add_issue_label,
            ["--label", "some-label"],  # Missing --issue-number
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd
            ),
        )

    # Click should return error for missing required option
    assert result.exit_code != 0
    assert "issue-number" in result.output.lower()


def test_missing_label(tmp_path: Path) -> None:
    """Test error when label is missing."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            add_issue_label,
            ["--issue-number", "123"],  # Missing --label
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd
            ),
        )

    # Click should return error for missing required option
    assert result.exit_code != 0
    assert "label" in result.output.lower()
