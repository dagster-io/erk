"""Production implementation of GitHub issues using gh CLI."""

import json
import subprocess
from datetime import datetime
from pathlib import Path

from erk_shared.github.issues.abc import GitHubIssues
from erk_shared.github.issues.label_cache import RealLabelCache
from erk_shared.github.issues.types import (
    CreateIssueResult,
    IssueComment,
    IssueInfo,
    PRReference,
)
from erk_shared.subprocess_utils import execute_gh_command


class RealGitHubIssues(GitHubIssues):
    """Production implementation using gh CLI.

    All GitHub issue operations execute actual gh commands via subprocess.
    Maintains an internal label cache to avoid redundant API calls.
    """

    def __init__(self) -> None:
        """Initialize RealGitHubIssues."""
        self._label_cache: RealLabelCache | None = None

    def create_issue(
        self, repo_root: Path, title: str, body: str, labels: list[str]
    ) -> CreateIssueResult:
        """Create a new GitHub issue using gh CLI.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, etc.).
        """
        cmd = ["gh", "issue", "create", "--title", title, "--body", body]
        for label in labels:
            cmd.extend(["--label", label])

        stdout = execute_gh_command(cmd, repo_root)
        # gh issue create returns a URL like: https://github.com/owner/repo/issues/123
        url = stdout.strip()
        issue_number_str = url.rstrip("/").split("/")[-1]

        return CreateIssueResult(
            number=int(issue_number_str),
            url=url,
        )

    def get_issue(self, repo_root: Path, number: int) -> IssueInfo:
        """Fetch issue data using gh CLI REST API.

        Uses REST API instead of GraphQL to avoid hitting GraphQL rate limits.
        The {owner}/{repo} placeholders are auto-substituted by gh CLI.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, issue not found).
        """
        cmd = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/issues/{number}",
        ]
        stdout = execute_gh_command(cmd, repo_root)
        data = json.loads(stdout)

        return IssueInfo(
            number=data["number"],
            title=data["title"],
            body=data["body"] or "",  # REST can return null
            state=data["state"].upper(),  # Convert "open" -> "OPEN"
            url=data["html_url"],  # Different field name in REST API
            labels=[label["name"] for label in data.get("labels", [])],
            assignees=[assignee["login"] for assignee in data.get("assignees", [])],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
        )

    def add_comment(self, repo_root: Path, number: int, body: str) -> None:
        """Add comment to issue using gh CLI.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, issue not found).
        """
        cmd = ["gh", "issue", "comment", str(number), "--body", body]
        execute_gh_command(cmd, repo_root)

    def update_issue_body(self, repo_root: Path, number: int, body: str) -> None:
        """Update issue body using gh CLI.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, issue not found).
        """
        cmd = ["gh", "issue", "edit", str(number), "--body", body]
        execute_gh_command(cmd, repo_root)

    def list_issues(
        self,
        repo_root: Path,
        labels: list[str] | None = None,
        state: str | None = None,
        limit: int | None = None,
    ) -> list[IssueInfo]:
        """Query issues using gh CLI.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated).
        """
        cmd = [
            "gh",
            "issue",
            "list",
            "--json",
            "number,title,body,state,url,labels,assignees,createdAt,updatedAt",
        ]

        if labels:
            for label in labels:
                cmd.extend(["--label", label])

        if state:
            cmd.extend(["--state", state])

        if limit is not None:
            cmd.extend(["--limit", str(limit)])

        stdout = execute_gh_command(cmd, repo_root)
        data = json.loads(stdout)

        return [
            IssueInfo(
                number=issue["number"],
                title=issue["title"],
                body=issue["body"],
                state=issue["state"],
                url=issue["url"],
                labels=[label["name"] for label in issue.get("labels", [])],
                assignees=[assignee["login"] for assignee in issue.get("assignees", [])],
                created_at=datetime.fromisoformat(issue["createdAt"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(issue["updatedAt"].replace("Z", "+00:00")),
            )
            for issue in data
        ]

    def get_issue_comments(self, repo_root: Path, number: int) -> list[str]:
        """Fetch all comment bodies for an issue using gh CLI.

        Uses JSON array output format to preserve multi-line comment bodies.
        The jq expression "[.[].body]" wraps results in a JSON array, which
        is then parsed with json.loads() to correctly handle newlines within
        comment bodies (e.g., markdown content).

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, issue not found).
        """
        cmd = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/issues/{number}/comments",
            "--jq",
            "[.[].body]",  # JSON array format preserves multi-line bodies
        ]
        stdout = execute_gh_command(cmd, repo_root)

        if not stdout.strip():
            return []

        return json.loads(stdout)

    def get_issue_comments_with_urls(self, repo_root: Path, number: int) -> list[IssueComment]:
        """Fetch all comments with their URLs for an issue using gh CLI.

        Uses JSON array output format to preserve multi-line comment bodies
        and extract html_url, id, and author for each comment.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, issue not found).
        """
        cmd = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/issues/{number}/comments",
            "--jq",
            "[.[] | {body, url: .html_url, id, author: .user.login}]",
        ]
        stdout = execute_gh_command(cmd, repo_root)

        if not stdout.strip():
            return []

        data = json.loads(stdout)
        return [
            IssueComment(body=item["body"], url=item["url"], id=item["id"], author=item["author"])
            for item in data
        ]

    def ensure_label_exists(
        self,
        repo_root: Path,
        label: str,
        description: str,
        color: str,
    ) -> None:
        """Ensure label exists in repository, creating it if needed.

        Uses an internal cache to avoid redundant API calls across multiple
        ensure_label_exists calls within the same session.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated).
        """
        # Lazily initialize cache on first use
        if self._label_cache is None:
            self._label_cache = RealLabelCache(repo_root)

        # Fast path: if cached, skip API call entirely
        if self._label_cache.has(label):
            return

        # Check if label exists via API
        check_cmd = [
            "gh",
            "label",
            "list",
            "--json",
            "name",
            "--jq",
            f'.[] | select(.name == "{label}") | .name',
        ]
        stdout = execute_gh_command(check_cmd, repo_root)

        if stdout.strip():
            # Label exists - cache it for future calls
            self._label_cache.add(label)
            return

        # Create label
        create_cmd = [
            "gh",
            "label",
            "create",
            label,
            "--description",
            description,
            "--color",
            color,
        ]
        execute_gh_command(create_cmd, repo_root)

        # Cache newly created label
        self._label_cache.add(label)

    def ensure_label_on_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
        """Ensure label is present on issue using gh CLI (idempotent).

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, issue not found).
        The gh CLI --add-label operation is idempotent.
        """
        cmd = ["gh", "issue", "edit", str(issue_number), "--add-label", label]
        execute_gh_command(cmd, repo_root)

    def remove_label_from_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
        """Remove label from issue using gh CLI.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, issue not found).
        If the label doesn't exist on the issue, gh CLI handles gracefully.
        """
        cmd = ["gh", "issue", "edit", str(issue_number), "--remove-label", label]
        execute_gh_command(cmd, repo_root)

    def close_issue(self, repo_root: Path, number: int) -> None:
        """Close issue using gh CLI.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, issue not found).
        """
        cmd = ["gh", "issue", "close", str(number)]
        execute_gh_command(cmd, repo_root)

    def get_current_username(self) -> str | None:
        """Get current GitHub username via gh api user.

        Returns:
            GitHub username if authenticated, None otherwise
        """
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()

    def get_prs_referencing_issue(
        self,
        repo_root: Path,
        issue_number: int,
    ) -> list[PRReference]:
        """Get PRs referencing issue via REST timeline API.

        Uses the timeline endpoint to find cross-referenced PRs.
        """
        cmd = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/issues/{issue_number}/timeline",
            "--jq",
            '[.[] | select(.event == "cross-referenced") '
            "| select(.source.issue.pull_request) "
            "| .source.issue | {number, state, is_draft: .draft}]",
        ]
        stdout = execute_gh_command(cmd, repo_root)

        if not stdout.strip():
            return []

        data = json.loads(stdout)
        return [
            PRReference(
                number=item["number"],
                state=item["state"].upper(),  # Normalize to "OPEN"/"CLOSED"
                is_draft=item.get("is_draft") or False,  # Handle null/missing
            )
            for item in data
        ]

    def add_reaction_to_comment(
        self,
        repo_root: Path,
        comment_id: int,
        reaction: str,
    ) -> None:
        """Add a reaction to an issue/PR comment using gh API.

        Uses the REST API to add a reaction. The API is idempotent -
        adding the same reaction twice returns the existing reaction.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, comment not found).
        """
        cmd = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/issues/comments/{comment_id}/reactions",
            "-X",
            "POST",
            "-f",
            f"content={reaction}",
        ]
        execute_gh_command(cmd, repo_root)
