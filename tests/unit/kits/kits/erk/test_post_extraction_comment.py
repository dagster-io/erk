"""Unit tests for post_extraction_comment kit CLI command.

Tests posting extraction workflow status comments to GitHub issues.
Uses FakeGitHubIssues for fast, reliable testing.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk_kits.data.kits.erk.scripts.erk.post_extraction_comment import (
    _format_complete_comment,
    _format_failed_comment,
    _format_no_changes_comment,
    _format_started_comment,
    post_extraction_comment,
)
from erk_shared.context import ErkContext
from erk_shared.git.fake import FakeGit
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo


def make_issue_info(number: int) -> IssueInfo:
    """Create test IssueInfo with given number."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=f"Test Issue #{number}",
        body="Test issue body",
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=["raw-extraction"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )


# ============================================================================
# Pure Unit Tests (Layer 3) - No Dependencies
# ============================================================================


def test_format_started_comment_basic() -> None:
    """Test started comment formatting without workflow URL."""
    result = _format_started_comment(None)

    assert "⚙️ **Documentation extraction started**" in result
    assert "status: started" in result
    assert "started_at:" in result


def test_format_started_comment_with_workflow_url() -> None:
    """Test started comment includes workflow URL when provided."""
    url = "https://github.com/owner/repo/actions/runs/12345"
    result = _format_started_comment(url)

    assert "⚙️ **Documentation extraction started**" in result
    assert f"workflow_run_url: {url}" in result
    assert f"[View workflow run]({url})" in result


def test_format_failed_comment_basic() -> None:
    """Test failed comment formatting without optional args."""
    result = _format_failed_comment(None, None)

    assert "❌ **Documentation extraction failed**" in result
    assert "No session content was found" in result
    assert "/erk:create-extraction-plan" in result


def test_format_failed_comment_with_error_message() -> None:
    """Test failed comment includes error message."""
    result = _format_failed_comment(None, "Custom error occurred")

    assert "**Error:** Custom error occurred" in result


def test_format_failed_comment_with_workflow_url() -> None:
    """Test failed comment includes workflow URL."""
    url = "https://github.com/owner/repo/actions/runs/67890"
    result = _format_failed_comment(url, None)

    assert f"[View workflow run]({url})" in result


def test_format_complete_comment_basic() -> None:
    """Test complete comment formatting without PR URL."""
    result = _format_complete_comment(None)

    assert "✅ **Documentation extraction complete**" in result
    assert "status: complete" in result
    assert "completed_at:" in result


def test_format_complete_comment_with_pr_url() -> None:
    """Test complete comment includes PR URL."""
    pr_url = "https://github.com/owner/repo/pull/123"
    result = _format_complete_comment(pr_url)

    assert f"**PR:** {pr_url}" in result
    assert f"pr_url: {pr_url}" in result


def test_format_no_changes_comment() -> None:
    """Test no-changes comment formatting."""
    result = _format_no_changes_comment()

    assert "ℹ️ **No documentation changes needed**" in result
    assert "did not produce any documentation changes" in result


# ============================================================================
# Success Cases (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_post_started_comment_success(tmp_path: Path) -> None:
    """Test posting started status comment."""
    fake_gh = FakeGitHubIssues(issues={100: make_issue_info(100)})
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            post_extraction_comment,
            ["--issue-number", "100", "--status", "started"],
            obj=ErkContext.for_test(github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 100
    assert output["status"] == "started"

    # Verify comment was posted
    assert len(fake_gh.added_comments) == 1
    issue_number, comment_body, _comment_id = fake_gh.added_comments[0]
    assert issue_number == 100
    assert "Documentation extraction started" in comment_body


def test_post_started_comment_with_workflow_url(tmp_path: Path) -> None:
    """Test posting started comment with workflow URL."""
    fake_gh = FakeGitHubIssues(issues={200: make_issue_info(200)})
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            post_extraction_comment,
            [
                "--issue-number",
                "200",
                "--status",
                "started",
                "--workflow-run-url",
                "https://github.com/owner/repo/actions/runs/12345",
            ],
            obj=ErkContext.for_test(github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0
    _, comment_body, _comment_id = fake_gh.added_comments[0]
    assert "https://github.com/owner/repo/actions/runs/12345" in comment_body


def test_post_failed_comment_success(tmp_path: Path) -> None:
    """Test posting failed status comment."""
    fake_gh = FakeGitHubIssues(issues={300: make_issue_info(300)})
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            post_extraction_comment,
            [
                "--issue-number",
                "300",
                "--status",
                "failed",
                "--error-message",
                "Session content was malformed",
            ],
            obj=ErkContext.for_test(github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["status"] == "failed"

    _, comment_body, _comment_id = fake_gh.added_comments[0]
    assert "Documentation extraction failed" in comment_body
    assert "Session content was malformed" in comment_body


def test_post_complete_comment_success(tmp_path: Path) -> None:
    """Test posting complete status comment."""
    fake_gh = FakeGitHubIssues(issues={400: make_issue_info(400)})
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            post_extraction_comment,
            [
                "--issue-number",
                "400",
                "--status",
                "complete",
                "--pr-url",
                "https://github.com/owner/repo/pull/456",
            ],
            obj=ErkContext.for_test(github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["status"] == "complete"

    _, comment_body, _comment_id = fake_gh.added_comments[0]
    assert "Documentation extraction complete" in comment_body
    assert "https://github.com/owner/repo/pull/456" in comment_body


def test_post_no_changes_comment_success(tmp_path: Path) -> None:
    """Test posting no-changes status comment."""
    fake_gh = FakeGitHubIssues(issues={500: make_issue_info(500)})
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            post_extraction_comment,
            ["--issue-number", "500", "--status", "no-changes"],
            obj=ErkContext.for_test(github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["status"] == "no-changes"

    _, comment_body, _comment_id = fake_gh.added_comments[0]
    assert "No documentation changes needed" in comment_body


# ============================================================================
# Error Cases (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_post_comment_github_api_failure(tmp_path: Path) -> None:
    """Test error when GitHub API fails."""

    class FailingFakeGitHubIssues(FakeGitHubIssues):
        def add_comment(self, repo_root: Path, number: int, body: str) -> None:
            raise RuntimeError("GitHub API rate limit exceeded")

    fake_gh = FailingFakeGitHubIssues(issues={600: make_issue_info(600)})
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            post_extraction_comment,
            ["--issue-number", "600", "--status", "started"],
            obj=ErkContext.for_test(github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Failed to post comment" in output["error"]


# ============================================================================
# JSON Output Structure Tests
# ============================================================================


def test_json_output_structure_success(tmp_path: Path) -> None:
    """Test JSON output structure on success."""
    fake_gh = FakeGitHubIssues(issues={700: make_issue_info(700)})
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            post_extraction_comment,
            ["--issue-number", "700", "--status", "started"],
            obj=ErkContext.for_test(github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify required keys
    assert "success" in output
    assert "issue_number" in output
    assert "status" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)
    assert isinstance(output["status"], str)


def test_json_output_structure_error(tmp_path: Path) -> None:
    """Test JSON output structure on error."""

    class FailingFakeGitHubIssues(FakeGitHubIssues):
        def add_comment(self, repo_root: Path, number: int, body: str) -> None:
            raise RuntimeError("Error")

    fake_gh = FailingFakeGitHubIssues(issues={800: make_issue_info(800)})
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            post_extraction_comment,
            ["--issue-number", "800", "--status", "started"],
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
# Comment Content Verification Tests
# ============================================================================


def test_started_comment_contains_metadata(tmp_path: Path) -> None:
    """Test that started comment contains expected metadata structure."""
    fake_gh = FakeGitHubIssues(issues={900: make_issue_info(900)})
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            post_extraction_comment,
            [
                "--issue-number",
                "900",
                "--status",
                "started",
                "--workflow-run-url",
                "https://example.com/run/123",
            ],
            obj=ErkContext.for_test(github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0

    _, comment_body, _comment_id = fake_gh.added_comments[0]
    # Check for key structural elements
    assert "<details>" in comment_body
    assert "<summary>" in comment_body
    assert "```yaml" in comment_body
    assert "status: started" in comment_body
    assert "started_at:" in comment_body


def test_failed_comment_contains_retry_instructions(tmp_path: Path) -> None:
    """Test that failed comment contains retry instructions."""
    fake_gh = FakeGitHubIssues(issues={1000: make_issue_info(1000)})
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            post_extraction_comment,
            ["--issue-number", "1000", "--status", "failed"],
            obj=ErkContext.for_test(github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0

    _, comment_body, _comment_id = fake_gh.added_comments[0]
    assert "/erk:create-extraction-plan" in comment_body
    assert "retry" in comment_body.lower()


def test_complete_comment_contains_review_prompt(tmp_path: Path) -> None:
    """Test that complete comment prompts for review."""
    fake_gh = FakeGitHubIssues(issues={1100: make_issue_info(1100)})
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            post_extraction_comment,
            [
                "--issue-number",
                "1100",
                "--status",
                "complete",
                "--pr-url",
                "https://github.com/owner/repo/pull/999",
            ],
            obj=ErkContext.for_test(github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0

    _, comment_body, _comment_id = fake_gh.added_comments[0]
    assert "Please review the PR" in comment_body
