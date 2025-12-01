"""Production implementation of GitHub issues using gh CLI."""

import json
import subprocess
from datetime import datetime
from pathlib import Path

from erk_shared.github.issues.abc import GitHubIssues
from erk_shared.github.issues.types import CreateIssueResult, IssueInfo
from erk_shared.subprocess_utils import execute_gh_command


class RealGitHubIssues(GitHubIssues):
    """Production implementation using gh CLI.

    All GitHub issue operations execute actual gh commands via subprocess.
    """

    def __init__(self) -> None:
        """Initialize RealGitHubIssues."""

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
        """Fetch issue data using gh CLI.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, issue not found).
        """
        cmd = [
            "gh",
            "issue",
            "view",
            str(number),
            "--json",
            "number,title,body,state,url,labels,assignees,createdAt,updatedAt",
        ]
        stdout = execute_gh_command(cmd, repo_root)
        data = json.loads(stdout)

        return IssueInfo(
            number=data["number"],
            title=data["title"],
            body=data["body"],
            state=data["state"],
            url=data["url"],
            labels=[label["name"] for label in data.get("labels", [])],
            assignees=[assignee["login"] for assignee in data.get("assignees", [])],
            created_at=datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updatedAt"].replace("Z", "+00:00")),
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

    def get_multiple_issue_comments(
        self, repo_root: Path, issue_numbers: list[int]
    ) -> dict[int, list[str]]:
        """Fetch comments for multiple issues using GraphQL batch query.

        Uses GraphQL aliases to fetch all issue comments in a single API call,
        dramatically improving performance (10-50x faster than individual calls).
        """
        if not issue_numbers:
            return {}

        # Get owner and repo name (GraphQL doesn't support {owner}/{repo} placeholders)
        repo_info_cmd = ["gh", "repo", "view", "--json", "owner,name"]
        repo_info_stdout = execute_gh_command(repo_info_cmd, repo_root)
        repo_info = json.loads(repo_info_stdout)
        owner = repo_info["owner"]["login"]
        repo_name = repo_info["name"]

        # Build GraphQL query with aliases for each issue
        aliases = []
        for i, num in enumerate(issue_numbers):
            aliases.append(
                f"issue{i}: issue(number: {num}) {{ "
                f"number comments(first: 100) {{ nodes {{ body }} }} }}"
            )

        repo_query = f'repository(owner: "{owner}", name: "{repo_name}")'
        query = f"query {{ {repo_query} {{ " + " ".join(aliases) + " } }"

        cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
        stdout = execute_gh_command(cmd, repo_root)
        data = json.loads(stdout)

        # Parse results into dict[issue_number -> comments]
        result: dict[int, list[str]] = {}
        repository = data.get("data", {}).get("repository", {})

        for i, num in enumerate(issue_numbers):
            issue_data = repository.get(f"issue{i}")
            if issue_data and issue_data.get("comments"):
                comments = [
                    node["body"] for node in issue_data["comments"]["nodes"] if node.get("body")
                ]
                result[num] = comments
            else:
                result[num] = []

        return result

    def ensure_label_exists(
        self,
        repo_root: Path,
        label: str,
        description: str,
        color: str,
    ) -> None:
        """Ensure label exists in repository, creating it if needed.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated).
        """
        # Check if label exists
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

        # If label doesn't exist (empty output), create it
        if not stdout.strip():
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
