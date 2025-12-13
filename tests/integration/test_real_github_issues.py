"""Tests for RealGitHubIssues with mocked subprocess execution.

These tests verify that RealGitHubIssues correctly calls gh CLI commands and handles
responses. We use pytest monkeypatch to mock subprocess calls.
"""

import json
import subprocess
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from erk_shared.github.issues import RealGitHubIssues
from tests.integration.test_helpers import mock_subprocess_run


def test_create_issue_success(monkeypatch: MonkeyPatch) -> None:
    """Test create_issue calls gh CLI with correct arguments and parses URL."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        # gh issue create returns a URL, not JSON
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="https://github.com/owner/repo/issues/42\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.create_issue(
            Path("/repo"),
            title="Test Issue",
            body="Test body content",
            labels=["plan", "erk"],
        )

        # Verify issue number extracted from URL
        assert result.number == 42
        assert result.url == "https://github.com/owner/repo/issues/42"

        # Verify gh command structure
        assert len(created_commands) == 1
        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "issue"
        assert cmd[2] == "create"
        assert "--title" in cmd
        assert "Test Issue" in cmd
        assert "--body" in cmd
        assert "Test body content" in cmd
        assert "--label" in cmd
        assert "plan" in cmd
        assert "erk" in cmd
        # Verify --json and --jq are NOT used (they're not supported by gh issue create)
        assert "--json" not in cmd
        assert "--jq" not in cmd


def test_create_issue_multiple_labels(monkeypatch: MonkeyPatch) -> None:
    """Test create_issue includes all labels in command."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="https://github.com/owner/repo/issues/1\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.create_issue(
            Path("/repo"),
            title="Title",
            body="Body",
            labels=["label1", "label2", "label3"],
        )

        cmd = created_commands[0]
        # Each label should appear after --label
        assert cmd.count("--label") == 3
        assert "label1" in cmd
        assert "label2" in cmd
        assert "label3" in cmd


def test_create_issue_no_labels(monkeypatch: MonkeyPatch) -> None:
    """Test create_issue works with empty labels list."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="https://github.com/owner/repo/issues/1\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.create_issue(Path("/repo"), title="Title", body="Body", labels=[])

        cmd = created_commands[0]
        # No --label flags should be present
        assert "--label" not in cmd


def test_create_issue_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test create_issue raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("gh command failed: not authenticated")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()

        with pytest.raises(RuntimeError, match="not authenticated"):
            issues.create_issue(Path("/repo"), "Title", "Body", ["label"])


def test_get_issue_success(monkeypatch: MonkeyPatch) -> None:
    """Test get_issue calls gh REST API and parses response."""
    # REST API response format (differs from GraphQL):
    # - state: lowercase ("open" vs "OPEN")
    # - html_url instead of url
    # - created_at/updated_at with underscores
    issue_data = {
        "number": 42,
        "title": "Test Issue Title",
        "body": "Test issue body content",
        "state": "open",  # REST uses lowercase
        "html_url": "https://github.com/owner/repo/issues/42",  # REST uses html_url
        "labels": [{"name": "bug"}, {"name": "enhancement"}],
        "assignees": [{"login": "alice"}, {"login": "bob"}],
        "created_at": "2024-01-15T10:30:00Z",  # REST uses snake_case
        "updated_at": "2024-01-16T14:45:00Z",
    }

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(issue_data),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.get_issue(Path("/repo"), 42)

        assert result.number == 42
        assert result.title == "Test Issue Title"
        assert result.body == "Test issue body content"
        assert result.state == "OPEN"  # Normalized to uppercase
        assert result.url == "https://github.com/owner/repo/issues/42"


def test_get_issue_command_structure(monkeypatch: MonkeyPatch) -> None:
    """Test get_issue constructs correct gh REST API command."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        # REST API response format
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(
                {
                    "number": 123,
                    "title": "Title",
                    "body": "Body",
                    "state": "open",
                    "html_url": "http://url",
                    "labels": [],
                    "assignees": [],
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                }
            ),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.get_issue(Path("/repo"), 123)

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        # REST API endpoint with {owner}/{repo} placeholders
        assert cmd[2] == "repos/{owner}/{repo}/issues/123"


def test_get_issue_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test get_issue raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("Issue not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()

        with pytest.raises(RuntimeError, match="Issue not found"):
            issues.get_issue(Path("/repo"), 999)


def test_get_issue_null_body(monkeypatch: MonkeyPatch) -> None:
    """Test get_issue handles null body from REST API."""
    # REST API can return null for body when issue has no description
    issue_data = {
        "number": 42,
        "title": "Issue without body",
        "body": None,  # REST can return null
        "state": "open",
        "html_url": "https://github.com/owner/repo/issues/42",
        "labels": [],
        "assignees": [],
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-16T14:45:00Z",
    }

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(issue_data),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.get_issue(Path("/repo"), 42)

        assert result.body == ""  # null converted to empty string


def test_add_comment_success(monkeypatch: MonkeyPatch) -> None:
    """Test add_comment calls gh CLI with correct arguments."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.add_comment(Path("/repo"), 42, "This is my comment body")

        # Verify command structure
        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "issue"
        assert cmd[2] == "comment"
        assert cmd[3] == "42"
        assert "--body" in cmd
        assert "This is my comment body" in cmd


def test_add_comment_multiline_body(monkeypatch: MonkeyPatch) -> None:
    """Test add_comment handles multiline comment bodies."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        multiline_body = """First line of comment

Second line after blank line

Third line"""
        issues.add_comment(Path("/repo"), 10, multiline_body)

        cmd = created_commands[0]
        assert multiline_body in cmd


def test_add_comment_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test add_comment raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("Issue not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()

        with pytest.raises(RuntimeError, match="Issue not found"):
            issues.add_comment(Path("/repo"), 999, "Comment body")


def test_list_issues_all(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues without filters using REST API."""
    # REST API response format (differs from GraphQL):
    # - state: lowercase ("open" vs "OPEN")
    # - html_url instead of url
    # - created_at/updated_at with underscores
    # - user.login instead of author.login
    issues_data = [
        {
            "number": 1,
            "title": "Issue 1",
            "body": "Body 1",
            "state": "open",  # REST uses lowercase
            "html_url": "http://url/1",  # REST uses html_url
            "labels": [],
            "assignees": [],
            "created_at": "2024-01-01T00:00:00Z",  # REST uses snake_case
            "updated_at": "2024-01-01T00:00:00Z",
            "user": {"login": "user1"},  # REST uses user.login
        },
        {
            "number": 2,
            "title": "Issue 2",
            "body": "Body 2",
            "state": "closed",  # REST uses lowercase
            "html_url": "http://url/2",
            "labels": [],
            "assignees": [],
            "created_at": "2024-01-02T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "user": {"login": "user2"},
        },
    ]

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(issues_data),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.list_issues(Path("/repo"))

        assert len(result) == 2
        assert result[0].number == 1
        assert result[0].title == "Issue 1"
        assert result[0].state == "OPEN"  # Normalized to uppercase
        assert result[1].number == 2
        assert result[1].state == "CLOSED"  # Normalized to uppercase


def test_list_issues_with_state_filter(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues with state filter uses REST API query parameter."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.list_issues(Path("/repo"), state="open")

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        # REST API uses query parameter in URL, not --state flag
        endpoint = cmd[2]
        assert "repos/{owner}/{repo}/issues" in endpoint
        assert "state=open" in endpoint


def test_list_issues_with_labels_filter(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues with labels filter uses REST API comma-separated query parameter."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.list_issues(Path("/repo"), labels=["plan", "erk"])

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        # REST API uses comma-separated labels in query parameter
        endpoint = cmd[2]
        assert "repos/{owner}/{repo}/issues" in endpoint
        assert "labels=plan,erk" in endpoint


def test_list_issues_with_both_filters(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues with both labels and state filters uses REST API query parameters."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.list_issues(Path("/repo"), labels=["bug"], state="closed")

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        endpoint = cmd[2]
        assert "repos/{owner}/{repo}/issues" in endpoint
        assert "labels=bug" in endpoint
        assert "state=closed" in endpoint


def test_list_issues_rest_api_endpoint(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues uses REST API endpoint instead of GraphQL."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.list_issues(Path("/repo"))

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        # Uses REST API endpoint, not 'gh issue list --json'
        assert cmd[2] == "repos/{owner}/{repo}/issues"
        # No --json flag (gh api returns JSON by default)
        assert "--json" not in cmd


def test_list_issues_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("gh not authenticated")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()

        with pytest.raises(RuntimeError, match="not authenticated"):
            issues.list_issues(Path("/repo"))


def test_list_issues_empty_response(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues handles empty results."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.list_issues(Path("/repo"))

        assert result == []


def test_list_issues_null_body(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues handles null body from REST API."""
    # REST API can return null for body when issue has no description
    issues_data = [
        {
            "number": 42,
            "title": "Issue without body",
            "body": None,  # REST can return null
            "state": "open",
            "html_url": "https://github.com/owner/repo/issues/42",
            "labels": [],
            "assignees": [],
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-16T14:45:00Z",
            "user": {"login": "octocat"},
        }
    ]

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(issues_data),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.list_issues(Path("/repo"))

        assert len(result) == 1
        assert result[0].body == ""  # null converted to empty string


def test_list_issues_parses_all_fields(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues correctly parses all IssueInfo fields from REST API response."""
    # REST API response format (differs from GraphQL):
    # - state: lowercase ("open" vs "OPEN")
    # - html_url instead of url
    # - created_at/updated_at with underscores
    # - user.login instead of author.login
    issues_data = [
        {
            "number": 123,
            "title": "Complex Issue Title with Special Chars: / & <>",
            "body": "Multi-line\nbody\nwith\nlinebreaks",
            "state": "open",  # REST uses lowercase
            "html_url": "https://github.com/owner/repo/issues/123",  # REST uses html_url
            "labels": [{"name": "bug"}, {"name": "documentation"}],
            "assignees": [{"login": "alice"}],
            "created_at": "2024-01-15T10:30:00Z",  # REST uses snake_case
            "updated_at": "2024-01-20T16:45:00Z",
            "user": {"login": "author_name"},  # REST uses user.login
        }
    ]

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(issues_data),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.list_issues(Path("/repo"))

        assert len(result) == 1
        issue = result[0]
        assert issue.number == 123
        assert issue.title == "Complex Issue Title with Special Chars: / & <>"
        assert issue.body == "Multi-line\nbody\nwith\nlinebreaks"
        assert issue.state == "OPEN"  # Normalized to uppercase
        assert issue.url == "https://github.com/owner/repo/issues/123"
        assert issue.author == "author_name"


def test_list_issues_with_limit(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues respects limit parameter using REST API per_page."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.list_issues(Path("/repo"), limit=10)

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        # REST API uses per_page query parameter, not --limit flag
        endpoint = cmd[2]
        assert "repos/{owner}/{repo}/issues" in endpoint
        assert "per_page=10" in endpoint


def test_get_current_username_success(monkeypatch: MonkeyPatch) -> None:
    """Test get_current_username returns username when authenticated."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Verify correct command structure
        assert cmd == ["gh", "api", "user", "--jq", ".login"]
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="octocat\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.get_current_username()

        assert result == "octocat"


def test_get_current_username_not_authenticated(monkeypatch: MonkeyPatch) -> None:
    """Test get_current_username returns None when not authenticated."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=1,
            stdout="",
            stderr="error: not logged in",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.get_current_username()

        assert result is None


def test_get_current_username_strips_whitespace(monkeypatch: MonkeyPatch) -> None:
    """Test get_current_username strips trailing whitespace from output."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="  username-with-spaces  \n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.get_current_username()

        assert result == "username-with-spaces"


# ============================================================================
# update_issue_body() tests
# ============================================================================


def test_update_issue_body_success(monkeypatch: MonkeyPatch) -> None:
    """Test update_issue_body calls gh CLI with correct command structure."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.update_issue_body(Path("/repo"), 42, "Updated body content")

        # Verify command structure
        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "issue"
        assert cmd[2] == "edit"
        assert cmd[3] == "42"
        assert "--body" in cmd
        assert "Updated body content" in cmd


def test_update_issue_body_multiline(monkeypatch: MonkeyPatch) -> None:
    """Test update_issue_body handles multiline body content."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        multiline_body = """# Heading

Paragraph with **bold** text.

- List item 1
- List item 2"""
        issues.update_issue_body(Path("/repo"), 10, multiline_body)

        cmd = created_commands[0]
        assert multiline_body in cmd


def test_update_issue_body_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test update_issue_body raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("Issue not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()

        with pytest.raises(RuntimeError, match="Issue not found"):
            issues.update_issue_body(Path("/repo"), 999, "New body")


# ============================================================================
# get_issue_comments() tests
# ============================================================================


def test_get_issue_comments_success(monkeypatch: MonkeyPatch) -> None:
    """Test get_issue_comments parses comment bodies correctly."""
    # JSON array output from jq "[.[].body]"
    json_output = json.dumps(["First comment", "Second comment", "Third comment"])

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json_output,
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.get_issue_comments(Path("/repo"), 42)

        assert result == ["First comment", "Second comment", "Third comment"]


def test_get_issue_comments_empty(monkeypatch: MonkeyPatch) -> None:
    """Test get_issue_comments handles no comments."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.get_issue_comments(Path("/repo"), 42)

        assert result == []


def test_get_issue_comments_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test get_issue_comments raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("Issue not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()

        with pytest.raises(RuntimeError, match="Issue not found"):
            issues.get_issue_comments(Path("/repo"), 999)


def test_get_issue_comments_multiline_bodies_preserved(monkeypatch: MonkeyPatch) -> None:
    """Test multi-line comment bodies are preserved as single list items.

    This is the critical bug fix test. The previous implementation used
    jq ".[].body" with split("\\n") which incorrectly split multi-line
    markdown comments into separate list items.

    The fix uses JSON array output format which preserves newlines within
    comment bodies.
    """
    # Simulate JSON array output from jq "[.[].body]"
    # This preserves multi-line bodies correctly
    json_output = json.dumps(
        [
            "Line 1\nLine 2\nLine 3",  # Multi-line first comment
            "Single line comment",  # Single line
            "Another\nmulti-line\ncomment",  # Another multi-line
        ]
    )

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json_output,
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.get_issue_comments(Path("/repo"), 42)

        # Should be 3 comments, NOT 8 (which would happen with split("\n"))
        assert len(result) == 3
        assert result[0] == "Line 1\nLine 2\nLine 3"
        assert result[1] == "Single line comment"
        assert result[2] == "Another\nmulti-line\ncomment"


def test_get_issue_comments_with_plan_markers(monkeypatch: MonkeyPatch) -> None:
    """Test comment containing plan markers preserves multi-line structure.

    This verifies the specific use case from Issue #1221 where a 299-line
    plan comment was being corrupted because newlines split it into
    separate "comments".
    """
    plan_comment = """<!-- erk:plan-content -->
# Plan: Test Implementation

## Step 1
Implementation details with newlines and formatting.

## Step 2
More details across multiple lines.

<!-- /erk:plan-content -->"""

    json_output = json.dumps([plan_comment])

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json_output,
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.get_issue_comments(Path("/repo"), 42)

        # Should be exactly ONE comment with all content intact
        assert len(result) == 1
        assert "<!-- erk:plan-content -->" in result[0]
        assert "<!-- /erk:plan-content -->" in result[0]
        assert "## Step 1" in result[0]
        assert "## Step 2" in result[0]


def test_get_issue_comments_command_uses_json_array_output(monkeypatch: MonkeyPatch) -> None:
    """Test get_issue_comments uses jq array format for reliable parsing."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",  # Empty JSON array
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.get_issue_comments(Path("/repo"), 42)

        # Verify command structure
        cmd = created_commands[0]
        assert "gh" in cmd
        assert "api" in cmd
        assert "--jq" in cmd
        # The jq expression should output a JSON array, not raw lines
        jq_idx = cmd.index("--jq") + 1
        jq_expr = cmd[jq_idx]
        # Should use [.[].body] not .[].body
        assert jq_expr.startswith("[") and jq_expr.endswith("]"), (
            f"jq expression should wrap in array brackets: {jq_expr}"
        )


# ============================================================================
# ensure_label_exists() tests
# ============================================================================


def test_ensure_label_exists_creates_new(monkeypatch: MonkeyPatch) -> None:
    """Test ensure_label_exists creates label when it doesn't exist."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        # First call: label list (returns empty - label doesn't exist)
        if "label" in cmd and "list" in cmd:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="",
                stderr="",
            )
        # Second call: label create
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.ensure_label_exists(
            Path("/repo"),
            label="erk-plan",
            description="Implementation plan",
            color="0E8A16",
        )

        # Should have made 2 calls: list then create
        assert len(created_commands) == 2

        # Verify create command structure
        create_cmd = created_commands[1]
        assert create_cmd[0] == "gh"
        assert create_cmd[1] == "label"
        assert create_cmd[2] == "create"
        assert "erk-plan" in create_cmd
        assert "--description" in create_cmd
        assert "Implementation plan" in create_cmd
        assert "--color" in create_cmd
        assert "0E8A16" in create_cmd


def test_ensure_label_exists_already_exists(monkeypatch: MonkeyPatch) -> None:
    """Test ensure_label_exists is no-op when label already exists."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        # Label already exists
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="erk-plan",  # Non-empty output means label exists
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.ensure_label_exists(
            Path("/repo"),
            label="erk-plan",
            description="Implementation plan",
            color="0E8A16",
        )

        # Should have made only 1 call: list (no create needed)
        assert len(created_commands) == 1
        assert "list" in created_commands[0]


def test_ensure_label_exists_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test ensure_label_exists raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("gh not authenticated")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()

        with pytest.raises(RuntimeError, match="not authenticated"):
            issues.ensure_label_exists(Path("/repo"), "label", "desc", "color")


# ============================================================================
# ensure_label_on_issue() tests
# ============================================================================


def test_ensure_label_on_issue_success(monkeypatch: MonkeyPatch) -> None:
    """Test ensure_label_on_issue calls gh CLI with correct command structure."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.ensure_label_on_issue(Path("/repo"), 42, "erk-plan")

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "issue"
        assert cmd[2] == "edit"
        assert cmd[3] == "42"
        assert "--add-label" in cmd
        assert "erk-plan" in cmd


def test_ensure_label_on_issue_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test ensure_label_on_issue raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("Issue not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()

        with pytest.raises(RuntimeError, match="Issue not found"):
            issues.ensure_label_on_issue(Path("/repo"), 999, "label")


# ============================================================================
# remove_label_from_issue() tests
# ============================================================================


def test_remove_label_from_issue_success(monkeypatch: MonkeyPatch) -> None:
    """Test remove_label_from_issue calls gh CLI with correct command structure."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.remove_label_from_issue(Path("/repo"), 42, "bug")

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "issue"
        assert cmd[2] == "edit"
        assert cmd[3] == "42"
        assert "--remove-label" in cmd
        assert "bug" in cmd


def test_remove_label_from_issue_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test remove_label_from_issue raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("Issue not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()

        with pytest.raises(RuntimeError, match="Issue not found"):
            issues.remove_label_from_issue(Path("/repo"), 999, "label")


# ============================================================================
# close_issue() tests
# ============================================================================


def test_close_issue_success(monkeypatch: MonkeyPatch) -> None:
    """Test close_issue calls gh CLI with correct command structure."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.close_issue(Path("/repo"), 42)

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "issue"
        assert cmd[2] == "close"
        assert cmd[3] == "42"


def test_close_issue_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test close_issue raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("Issue not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()

        with pytest.raises(RuntimeError, match="Issue not found"):
            issues.close_issue(Path("/repo"), 999)


# ============================================================================
# get_prs_referencing_issue() tests
# ============================================================================


def test_get_prs_referencing_issue_success(monkeypatch: MonkeyPatch) -> None:
    """Test get_prs_referencing_issue parses timeline API response correctly."""
    # JSON output from jq expression that filters cross-referenced PRs
    json_output = json.dumps(
        [
            {"number": 100, "state": "open", "is_draft": True},
            {"number": 101, "state": "closed", "is_draft": False},
        ]
    )

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json_output,
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.get_prs_referencing_issue(Path("/repo"), 42)

        assert len(result) == 2
        assert result[0].number == 100
        assert result[0].state == "OPEN"  # State is uppercased
        assert result[0].is_draft is True
        assert result[1].number == 101
        assert result[1].state == "CLOSED"
        assert result[1].is_draft is False


def test_get_prs_referencing_issue_empty(monkeypatch: MonkeyPatch) -> None:
    """Test get_prs_referencing_issue handles empty response."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.get_prs_referencing_issue(Path("/repo"), 42)

        assert result == []


def test_get_prs_referencing_issue_empty_array(monkeypatch: MonkeyPatch) -> None:
    """Test get_prs_referencing_issue handles empty JSON array."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.get_prs_referencing_issue(Path("/repo"), 42)

        assert result == []


def test_get_prs_referencing_issue_command_structure(monkeypatch: MonkeyPatch) -> None:
    """Test get_prs_referencing_issue constructs correct gh CLI command."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.get_prs_referencing_issue(Path("/repo"), 123)

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        # Should use timeline endpoint with issue number
        assert any("timeline" in arg for arg in cmd)
        assert any("123" in arg for arg in cmd)
        assert "--jq" in cmd


def test_get_prs_referencing_issue_handles_null_draft(monkeypatch: MonkeyPatch) -> None:
    """Test get_prs_referencing_issue handles null/missing is_draft field."""
    # Some PR responses may have null or missing draft field
    json_output = json.dumps(
        [
            {"number": 100, "state": "open", "is_draft": None},
            {"number": 101, "state": "open"},  # is_draft missing entirely
        ]
    )

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json_output,
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.get_prs_referencing_issue(Path("/repo"), 42)

        # Both should default to False when is_draft is null/missing
        assert len(result) == 2
        assert result[0].is_draft is False
        assert result[1].is_draft is False


def test_get_prs_referencing_issue_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test get_prs_referencing_issue raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("Issue not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()

        with pytest.raises(RuntimeError, match="Issue not found"):
            issues.get_prs_referencing_issue(Path("/repo"), 999)
