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

    def __init__(self, target_repo: str | None) -> None:
        """Initialize RealGitHubIssues.

        Args:
            target_repo: Target repository in "owner/repo" format.
                If set, all gh commands will use -R flag to target this repo.
                If None, gh CLI uses cwd-based repo detection (default behavior).
        """
        self._target_repo = target_repo
        self._label_cache: RealLabelCache | None = None

    @property
    def target_repo(self) -> str | None:
        """Read-only access to target repository for test assertions."""
        return self._target_repo

    def _build_gh_command(self, base_cmd: list[str]) -> list[str]:
        """Build gh command with optional -R flag for target repo.

        If target_repo is set, inserts -R owner/repo after 'gh' in the command.
        The -R flag must come immediately after 'gh' for most gh subcommands.

        Note: The -R flag is NOT supported by `gh api` - that subcommand uses
        {owner}/{repo} placeholders in the endpoint instead. For `gh api`
        commands, we substitute the placeholders with the target repo value.

        Args:
            base_cmd: Base command starting with 'gh'

        Returns:
            Command with -R flag inserted if target_repo is set,
            or with {owner}/{repo} substituted for gh api commands
        """
        if self._target_repo is None:
            return base_cmd
        # gh api doesn't support -R flag - substitute {owner}/{repo} in endpoint
        if len(base_cmd) > 1 and base_cmd[1] == "api":
            return [arg.replace("{owner}/{repo}", self._target_repo) for arg in base_cmd]
        # Insert -R owner/repo after 'gh' but before subcommand
        return [base_cmd[0], "-R", self._target_repo, *base_cmd[1:]]

    def create_issue(
        self, *, repo_root: Path, title: str, body: str, labels: list[str]
    ) -> CreateIssueResult:
        """Create a new GitHub issue using gh CLI REST API.

        Uses REST API instead of GraphQL (`gh issue create`) to avoid hitting
        GraphQL rate limits. GraphQL and REST have separate quotas.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, etc.).
        """
        # GH-API-AUDIT: REST - POST issues
        base_cmd = [
            "gh",
            "api",
            "repos/{owner}/{repo}/issues",
            "-X",
            "POST",
            "-f",
            f"title={title}",
            "-f",
            f"body={body}",
            "--jq",
            r'"\(.number) \(.html_url)"',
        ]
        for label in labels:
            base_cmd.extend(["-f", f"labels[]={label}"])

        cmd = self._build_gh_command(base_cmd)
        stdout = execute_gh_command(cmd, repo_root)
        # REST API returns JSON, --jq extracts "number url" format
        parts = stdout.strip().split(" ", 1)
        number = int(parts[0])
        url = parts[1]

        return CreateIssueResult(
            number=number,
            url=url,
        )

    def get_issue(self, repo_root: Path, number: int) -> IssueInfo:
        """Fetch issue data using gh CLI REST API.

        Uses REST API instead of GraphQL to avoid hitting GraphQL rate limits.
        The {owner}/{repo} placeholders are auto-substituted by gh CLI.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, issue not found).
        """
        # GH-API-AUDIT: REST - GET issues/{number}
        base_cmd = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/issues/{number}",
        ]
        cmd = self._build_gh_command(base_cmd)
        stdout = execute_gh_command(cmd, repo_root)
        data = json.loads(stdout)

        # Extract author login (user who created the issue)
        author = data.get("user", {}).get("login", "")

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
            author=author,
        )

    def add_comment(self, repo_root: Path, number: int, body: str) -> int:
        """Add comment to issue using gh CLI.

        Returns the comment ID from the created comment.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, issue not found).
        """
        # GH-API-AUDIT: REST - POST issues/{number}/comments
        base_cmd = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/issues/{number}/comments",
            "-X",
            "POST",
            "-f",
            f"body={body}",
            "--jq",
            ".id",
        ]
        cmd = self._build_gh_command(base_cmd)
        stdout = execute_gh_command(cmd, repo_root)
        return int(stdout.strip())

    def update_issue_body(self, repo_root: Path, number: int, body: str) -> None:
        """Update issue body using gh CLI REST API.

        Uses REST API instead of GraphQL (`gh issue edit`) to avoid hitting
        GraphQL rate limits. GraphQL and REST have separate quotas.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, issue not found).
        """
        # GH-API-AUDIT: REST - PATCH issues/{number}
        base_cmd = [
            "gh",
            "api",
            "--method",
            "PATCH",
            f"repos/{{owner}}/{{repo}}/issues/{number}",
            "-f",
            f"body={body}",
        ]
        cmd = self._build_gh_command(base_cmd)
        execute_gh_command(cmd, repo_root)

    def list_issues(
        self,
        *,
        repo_root: Path,
        labels: list[str] | None = None,
        state: str | None = None,
        limit: int | None = None,
    ) -> list[IssueInfo]:
        """Query issues using gh CLI REST API.

        Uses REST API instead of GraphQL to avoid hitting GraphQL rate limits.
        The {owner}/{repo} placeholders are auto-substituted by gh CLI.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated).
        """
        # Build REST API endpoint with query parameters
        endpoint = "repos/{owner}/{repo}/issues"
        params: list[str] = []

        if labels:
            # REST API accepts comma-separated labels
            params.append(f"labels={','.join(labels)}")

        if state:
            params.append(f"state={state}")

        if limit is not None:
            params.append(f"per_page={limit}")

        if params:
            endpoint += "?" + "&".join(params)

        # GH-API-AUDIT: REST - GET issues (with filters)
        base_cmd = ["gh", "api", endpoint]
        cmd = self._build_gh_command(base_cmd)
        stdout = execute_gh_command(cmd, repo_root)
        data = json.loads(stdout)

        return [
            IssueInfo(
                number=issue["number"],
                title=issue["title"],
                body=issue["body"] or "",  # REST can return null
                state=issue["state"].upper(),  # Convert "open" -> "OPEN"
                url=issue["html_url"],  # Different field name in REST
                labels=[label["name"] for label in issue.get("labels", [])],
                assignees=[assignee["login"] for assignee in issue.get("assignees", [])],
                created_at=datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(issue["updated_at"].replace("Z", "+00:00")),
                author=issue.get("user", {}).get("login", ""),  # user.login not author.login
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
        # GH-API-AUDIT: REST - GET issues/{number}/comments
        base_cmd = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/issues/{number}/comments",
            "--jq",
            "[.[].body]",  # JSON array format preserves multi-line bodies
        ]
        cmd = self._build_gh_command(base_cmd)
        stdout = execute_gh_command(cmd, repo_root)

        if not stdout.strip():
            return []

        return json.loads(stdout)

    def get_comment_by_id(self, repo_root: Path, comment_id: int) -> str:
        """Fetch a single comment body by its ID using gh CLI.

        Uses the REST API endpoint to get a specific comment.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, comment not found).
        """
        # GH-API-AUDIT: REST - GET issues/comments/{id}
        base_cmd = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/issues/comments/{comment_id}",
            "--jq",
            ".body",
        ]
        cmd = self._build_gh_command(base_cmd)
        stdout = execute_gh_command(cmd, repo_root)
        return stdout

    def get_issue_comments_with_urls(self, repo_root: Path, number: int) -> list[IssueComment]:
        """Fetch all comments with their URLs for an issue using gh CLI.

        Uses JSON array output format to preserve multi-line comment bodies
        and extract html_url, id, and author for each comment.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, issue not found).
        """
        # GH-API-AUDIT: REST - GET issues/{number}/comments
        base_cmd = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/issues/{number}/comments",
            "--jq",
            "[.[] | {body, url: .html_url, id, author: .user.login}]",
        ]
        cmd = self._build_gh_command(base_cmd)
        stdout = execute_gh_command(cmd, repo_root)

        if not stdout.strip():
            return []

        data = json.loads(stdout)
        return [
            IssueComment(body=item["body"], url=item["url"], id=item["id"], author=item["author"])
            for item in data
        ]

    def ensure_label_exists(
        self, *, repo_root: Path, label: str, description: str, color: str
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

        # GH-API-AUDIT: REST - GET labels
        base_check_cmd = [
            "gh",
            "api",
            "repos/{owner}/{repo}/labels",
            "--jq",
            f'.[] | select(.name == "{label}") | .name',
        ]
        check_cmd = self._build_gh_command(base_check_cmd)
        stdout = execute_gh_command(check_cmd, repo_root)

        if stdout.strip():
            # Label exists - cache it for future calls
            self._label_cache.add(label)
            return

        # GH-API-AUDIT: REST - gh label create uses REST
        base_create_cmd = [
            "gh",
            "label",
            "create",
            label,
            "--description",
            description,
            "--color",
            color,
        ]
        create_cmd = self._build_gh_command(base_create_cmd)
        execute_gh_command(create_cmd, repo_root)

        # Cache newly created label
        self._label_cache.add(label)

    def label_exists(self, repo_root: Path, label: str) -> bool:
        """Check if label exists in repository (read-only).

        Uses the label cache if available to avoid redundant API calls.
        """
        # Lazily initialize cache on first use
        if self._label_cache is None:
            self._label_cache = RealLabelCache(repo_root)

        # Fast path: if cached, we know it exists
        if self._label_cache.has(label):
            return True

        # GH-API-AUDIT: REST - GET labels
        base_check_cmd = [
            "gh",
            "api",
            "repos/{owner}/{repo}/labels",
            "--jq",
            f'.[] | select(.name == "{label}") | .name',
        ]
        check_cmd = self._build_gh_command(base_check_cmd)
        stdout = execute_gh_command(check_cmd, repo_root)

        if stdout.strip():
            # Label exists - cache it for future calls
            self._label_cache.add(label)
            return True

        return False

    def ensure_label_on_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
        """Ensure label is present on issue using gh CLI REST API (idempotent).

        Uses REST API instead of GraphQL (`gh issue edit`) to avoid hitting
        GraphQL rate limits. GraphQL and REST have separate quotas.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, issue not found).
        The REST API POST labels operation is idempotent.
        """
        # GH-API-AUDIT: REST - POST issues/{number}/labels
        base_cmd = [
            "gh",
            "api",
            "--method",
            "POST",
            f"repos/{{owner}}/{{repo}}/issues/{issue_number}/labels",
            "-f",
            f"labels[]={label}",
        ]
        cmd = self._build_gh_command(base_cmd)
        execute_gh_command(cmd, repo_root)

    def remove_label_from_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
        """Remove label from issue using gh CLI REST API.

        Uses REST API instead of GraphQL (`gh issue edit`) to avoid hitting
        GraphQL rate limits. GraphQL and REST have separate quotas.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, issue not found).
        If the label doesn't exist on the issue, the API returns 404.
        """
        # GH-API-AUDIT: REST - DELETE issues/{number}/labels/{name}
        base_cmd = [
            "gh",
            "api",
            "--method",
            "DELETE",
            f"repos/{{owner}}/{{repo}}/issues/{issue_number}/labels/{label}",
        ]
        cmd = self._build_gh_command(base_cmd)
        execute_gh_command(cmd, repo_root)

    def close_issue(self, repo_root: Path, number: int) -> None:
        """Close issue using gh CLI REST API.

        Uses REST API instead of GraphQL (`gh issue close`) to avoid hitting
        GraphQL rate limits. GraphQL and REST have separate quotas.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, issue not found).
        """
        # GH-API-AUDIT: REST - PATCH issues/{number}
        base_cmd = [
            "gh",
            "api",
            "--method",
            "PATCH",
            f"repos/{{owner}}/{{repo}}/issues/{number}",
            "-f",
            "state=closed",
        ]
        cmd = self._build_gh_command(base_cmd)
        execute_gh_command(cmd, repo_root)

    def get_current_username(self) -> str | None:
        """Get current GitHub username via gh api user.

        Returns:
            GitHub username if authenticated, None otherwise
        """
        # GH-API-AUDIT: REST - GET user
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
        # GH-API-AUDIT: REST - GET issues/{number}/timeline
        base_cmd = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/issues/{issue_number}/timeline",
            "--jq",
            '[.[] | select(.event == "cross-referenced") '
            "| select(.source.issue.pull_request) "
            "| .source.issue | {number, state, is_draft: .draft}]",
        ]
        cmd = self._build_gh_command(base_cmd)
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
        # GH-API-AUDIT: REST - POST issues/comments/{id}/reactions
        base_cmd = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/issues/comments/{comment_id}/reactions",
            "-X",
            "POST",
            "-f",
            f"content={reaction}",
        ]
        cmd = self._build_gh_command(base_cmd)
        execute_gh_command(cmd, repo_root)

    def update_comment(
        self,
        repo_root: Path,
        comment_id: int,
        body: str,
    ) -> None:
        """Update an issue comment's body using gh API.

        Uses the REST API to update the comment body.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, comment not found).
        """
        # GH-API-AUDIT: REST - PATCH issues/comments/{id}
        base_cmd = [
            "gh",
            "api",
            "--method",
            "PATCH",
            f"repos/{{owner}}/{{repo}}/issues/comments/{comment_id}",
            "-f",
            f"body={body}",
        ]
        cmd = self._build_gh_command(base_cmd)
        execute_gh_command(cmd, repo_root)
