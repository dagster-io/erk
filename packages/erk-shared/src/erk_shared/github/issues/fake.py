"""In-memory fake implementation of GitHub issues for testing."""

from datetime import UTC, datetime
from pathlib import Path

from erk_shared.github.issues.abc import GitHubIssues
from erk_shared.github.issues.types import (
    CreateIssueResult,
    IssueComment,
    IssueInfo,
    PRReference,
)


class FakeGitHubIssues(GitHubIssues):
    """In-memory fake implementation for testing.

    All state is provided via constructor using keyword arguments.
    """

    def __init__(
        self,
        *,
        issues: dict[int, IssueInfo] | None = None,
        next_issue_number: int = 1,
        labels: set[str] | None = None,
        comments: dict[int, list[str]] | None = None,
        comments_with_urls: dict[int, list[IssueComment]] | None = None,
        username: str | None = "testuser",
        pr_references: dict[int, list[PRReference]] | None = None,
        add_reaction_error: str | None = None,
        get_comments_error: str | None = None,
    ) -> None:
        """Create FakeGitHubIssues with pre-configured state.

        Args:
            issues: Mapping of issue number -> IssueInfo
            next_issue_number: Next issue number to assign (for predictable testing)
            labels: Set of existing label names in the repository
            comments: Mapping of issue number -> list of comment bodies
            comments_with_urls: Mapping of issue number -> list of IssueComment
            username: GitHub username to return (default: "testuser", None means
                not authenticated)
            pr_references: Mapping of issue number -> list of PRReference for
                get_prs_referencing_issue()
            add_reaction_error: If set, add_reaction_to_comment raises RuntimeError
                with this message
            get_comments_error: If set, get_issue_comments_with_urls raises
                RuntimeError with this message
        """
        self._issues = issues or {}
        self._next_issue_number = next_issue_number
        self._labels = labels or set()
        self._comments = comments or {}
        self._comments_with_urls = comments_with_urls or {}
        self._username = username
        self._pr_references = pr_references or {}
        self._add_reaction_error = add_reaction_error
        self._get_comments_error = get_comments_error
        self._created_issues: list[tuple[str, str, list[str]]] = []
        self._added_comments: list[tuple[int, str, int]] = []  # (issue_number, body, comment_id)
        self._created_labels: list[tuple[str, str, str]] = []
        self._closed_issues: list[int] = []
        self._added_reactions: list[tuple[int, str]] = []
        self._next_comment_id = 1000  # Start at 1000 to distinguish from issue numbers

    @property
    def created_issues(self) -> list[tuple[str, str, list[str]]]:
        """Read-only access to created issues for test assertions.

        Returns list of (title, body, labels) tuples.
        """
        return self._created_issues

    @property
    def added_comments(self) -> list[tuple[int, str, int]]:
        """Read-only access to added comments for test assertions.

        Returns list of (issue_number, body, comment_id) tuples.
        """
        return self._added_comments

    @property
    def created_labels(self) -> list[tuple[str, str, str]]:
        """Read-only access to created labels for test assertions.

        Returns list of (label, description, color) tuples.
        """
        return self._created_labels

    @property
    def closed_issues(self) -> list[int]:
        """Read-only access to closed issues for test assertions.

        Returns list of issue numbers that were closed.
        """
        return self._closed_issues

    @property
    def labels(self) -> set[str]:
        """Read-only access to label names in the repository.

        Returns set of label names.
        """
        return self._labels.copy()

    @property
    def added_reactions(self) -> list[tuple[int, str]]:
        """Read-only access to added reactions for test assertions.

        Returns list of (comment_id, reaction) tuples.
        """
        return self._added_reactions

    def create_issue(
        self, repo_root: Path, title: str, body: str, labels: list[str]
    ) -> CreateIssueResult:
        """Create issue in fake storage and track mutation."""
        issue_number = self._next_issue_number
        self._next_issue_number += 1

        # Create realistic fake URL for testing
        url = f"https://github.com/test-owner/test-repo/issues/{issue_number}"

        now = datetime.now(UTC)
        # Use configured username as author for created issues
        author = self._username or "test-user"
        self._issues[issue_number] = IssueInfo(
            number=issue_number,
            title=title,
            body=body,
            state="OPEN",
            url=url,
            labels=labels,
            assignees=[],
            created_at=now,
            updated_at=now,
            author=author,
        )
        self._created_issues.append((title, body, labels))

        return CreateIssueResult(number=issue_number, url=url)

    def get_issue(self, repo_root: Path, number: int) -> IssueInfo:
        """Get issue from fake storage.

        Raises:
            RuntimeError: If issue number not found (simulates gh CLI error)
        """
        if number not in self._issues:
            msg = f"Issue #{number} not found"
            raise RuntimeError(msg)
        return self._issues[number]

    def add_comment(self, repo_root: Path, number: int, body: str) -> int:
        """Record comment in mutation tracking and return generated comment ID.

        Raises:
            RuntimeError: If issue number not found (simulates gh CLI error)
        """
        if number not in self._issues:
            msg = f"Issue #{number} not found"
            raise RuntimeError(msg)
        comment_id = self._next_comment_id
        self._next_comment_id += 1
        self._added_comments.append((number, body, comment_id))
        return comment_id

    def update_issue_body(self, repo_root: Path, number: int, body: str) -> None:
        """Update issue body in fake storage.

        Raises:
            RuntimeError: If issue number not found (simulates gh CLI error)
        """
        if number not in self._issues:
            msg = f"Issue #{number} not found"
            raise RuntimeError(msg)

        # Update the issue body in-place (creates new IssueInfo with updated body)
        old_issue = self._issues[number]
        updated_issue = IssueInfo(
            number=old_issue.number,
            title=old_issue.title,
            body=body,  # New body
            state=old_issue.state,
            url=old_issue.url,
            labels=old_issue.labels,
            assignees=old_issue.assignees,
            created_at=old_issue.created_at,
            updated_at=datetime.now(UTC),  # Update timestamp
            author=old_issue.author,
        )
        self._issues[number] = updated_issue

    def list_issues(
        self,
        repo_root: Path,
        labels: list[str] | None = None,
        state: str | None = None,
        limit: int | None = None,
    ) -> list[IssueInfo]:
        """Query issues from fake storage.

        Filters issues by labels (AND logic) and state.
        """
        issues = list(self._issues.values())

        # Filter by labels (AND logic - issue must have ALL specified labels)
        if labels:
            label_set = set(labels)
            issues = [issue for issue in issues if label_set.issubset(set(issue.labels))]

        if state and state != "all":
            state_upper = state.upper()
            issues = [issue for issue in issues if issue.state == state_upper]

        if limit is not None:
            issues = issues[:limit]

        return issues

    def get_issue_comments(self, repo_root: Path, number: int) -> list[str]:
        """Get comments for issue from fake storage.

        Returns:
            List of comment bodies, or empty list if no comments exist
        """
        return self._comments.get(number, [])

    def get_comment_by_id(self, repo_root: Path, comment_id: int) -> str:
        """Get a single comment body by ID from fake storage.

        Searches both pre-configured comments (from constructor) and
        dynamically added comments (from add_comment).

        Raises:
            RuntimeError: If comment ID not found (simulates gh CLI error)
        """
        # First check pre-configured comments in _comments_with_urls
        for comments_list in self._comments_with_urls.values():
            for comment in comments_list:
                if comment.id == comment_id:
                    return comment.body

        # Then check dynamically added comments
        for _, body, cid in self._added_comments:
            if cid == comment_id:
                return body

        msg = f"Comment #{comment_id} not found"
        raise RuntimeError(msg)

    def get_issue_comments_with_urls(self, repo_root: Path, number: int) -> list[IssueComment]:
        """Get comments with URLs for issue from fake storage.

        Returns:
            List of IssueComment objects (with body, url, id, author),
            or empty list if no comments exist

        Raises:
            RuntimeError: If get_comments_error was set in constructor
        """
        if self._get_comments_error is not None:
            raise RuntimeError(self._get_comments_error)
        return self._comments_with_urls.get(number, [])

    def ensure_label_exists(
        self,
        repo_root: Path,
        label: str,
        description: str,
        color: str,
    ) -> None:
        """Ensure label exists in fake storage, creating if needed."""
        if label not in self._labels:
            self._labels.add(label)
            self._created_labels.append((label, description, color))

    def ensure_label_on_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
        """Ensure label is present on issue in fake storage (idempotent).

        Raises:
            RuntimeError: If issue number not found (simulates gh CLI error)
        """
        if issue_number not in self._issues:
            msg = f"Issue #{issue_number} not found"
            raise RuntimeError(msg)

        # Get current issue and create updated version with new label (if not present)
        current_issue = self._issues[issue_number]
        if label not in current_issue.labels:
            updated_labels = current_issue.labels + [label]
            self._issues[issue_number] = IssueInfo(
                number=current_issue.number,
                title=current_issue.title,
                body=current_issue.body,
                state=current_issue.state,
                url=current_issue.url,
                labels=updated_labels,
                assignees=current_issue.assignees,
                created_at=current_issue.created_at,
                updated_at=current_issue.updated_at,
                author=current_issue.author,
            )

    def remove_label_from_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
        """Remove label from issue in fake storage.

        Raises:
            RuntimeError: If issue number not found (simulates gh CLI error)
        """
        if issue_number not in self._issues:
            msg = f"Issue #{issue_number} not found"
            raise RuntimeError(msg)

        # Get current issue and create updated version without the label
        current_issue = self._issues[issue_number]
        if label in current_issue.labels:
            updated_labels = [lbl for lbl in current_issue.labels if lbl != label]
            self._issues[issue_number] = IssueInfo(
                number=current_issue.number,
                title=current_issue.title,
                body=current_issue.body,
                state=current_issue.state,
                url=current_issue.url,
                labels=updated_labels,
                assignees=current_issue.assignees,
                created_at=current_issue.created_at,
                updated_at=current_issue.updated_at,
                author=current_issue.author,
            )

    def close_issue(self, repo_root: Path, number: int) -> None:
        """Close issue in fake storage.

        Raises:
            RuntimeError: If issue number not found (simulates gh CLI error)
        """
        if number not in self._issues:
            msg = f"Issue #{number} not found"
            raise RuntimeError(msg)

        # Update issue state to closed
        current_issue = self._issues[number]
        self._issues[number] = IssueInfo(
            number=current_issue.number,
            title=current_issue.title,
            body=current_issue.body,
            state="closed",
            url=current_issue.url,
            labels=current_issue.labels,
            assignees=current_issue.assignees,
            created_at=current_issue.created_at,
            updated_at=current_issue.updated_at,
            author=current_issue.author,
        )
        self._closed_issues.append(number)

    def get_current_username(self) -> str | None:
        """Return configured username from constructor.

        Returns:
            Username configured in constructor (default: "testuser")
        """
        return self._username

    def get_prs_referencing_issue(
        self,
        repo_root: Path,
        issue_number: int,
    ) -> list[PRReference]:
        """Get PRs referencing issue from configured state.

        Returns:
            List of PRReference from pr_references constructor arg,
            or empty list if no references configured for this issue.
        """
        return self._pr_references.get(issue_number, [])

    def add_reaction_to_comment(
        self,
        repo_root: Path,
        comment_id: int,
        reaction: str,
    ) -> None:
        """Record reaction in mutation tracking.

        Note: Does not validate comment_id exists. Real API is idempotent.

        Raises:
            RuntimeError: If add_reaction_error was set in constructor
        """
        if self._add_reaction_error is not None:
            raise RuntimeError(self._add_reaction_error)
        self._added_reactions.append((comment_id, reaction))
