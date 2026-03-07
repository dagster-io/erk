"""Abstract interface for remote GitHub operations without a local git clone.

This gateway enables GitHub operations (branch creation, file commits, PR management,
workflow dispatch) using the GitHub REST API directly, without requiring a local
git repository. All methods take explicit owner/repo parameters.
"""

from abc import ABC, abstractmethod

from erk_shared.gateway.github.issues.types import IssueInfo, IssueNotFound, PRReference


class RemoteGitHub(ABC):
    """GitHub operations that don't require a local git clone.

    Every method takes explicit owner/repo parameters instead of repo_root: Path.
    Uses the GitHub REST API via HttpClient.
    """

    @abstractmethod
    def get_authenticated_user(self) -> str:
        """Get the username of the authenticated GitHub user.

        Returns:
            GitHub username string
        """
        ...

    @abstractmethod
    def get_default_branch_name(self, *, owner: str, repo: str) -> str:
        """Get the default branch name for a repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Default branch name (e.g., "main" or "master")
        """
        ...

    @abstractmethod
    def get_default_branch_sha(self, *, owner: str, repo: str) -> str:
        """Get the SHA of the default branch HEAD.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            SHA string of the default branch HEAD commit
        """
        ...

    @abstractmethod
    def create_ref(self, *, owner: str, repo: str, ref: str, sha: str) -> None:
        """Create a git reference (branch).

        Args:
            owner: Repository owner
            repo: Repository name
            ref: Full ref name (e.g., "refs/heads/my-branch")
            sha: SHA to point the ref at
        """
        ...

    @abstractmethod
    def create_file_commit(
        self,
        *,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str,
    ) -> str:
        """Create a file commit using the GitHub Contents API.

        Args:
            owner: Repository owner
            repo: Repository name
            path: File path in the repo (e.g., ".erk/impl-context/prompt.md")
            content: File content (will be base64-encoded)
            message: Commit message
            branch: Branch to commit to

        Returns:
            SHA of the new commit
        """
        ...

    @abstractmethod
    def create_pull_request(
        self,
        *,
        owner: str,
        repo: str,
        head: str,
        base: str,
        title: str,
        body: str,
        draft: bool,
    ) -> int:
        """Create a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            head: Branch with changes
            base: Branch to merge into
            title: PR title
            body: PR body
            draft: Whether to create as draft

        Returns:
            PR number
        """
        ...

    @abstractmethod
    def update_pull_request_body(
        self,
        *,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
    ) -> None:
        """Update a pull request's body.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            body: New body content
        """
        ...

    @abstractmethod
    def add_labels(
        self,
        *,
        owner: str,
        repo: str,
        issue_number: int,
        labels: tuple[str, ...],
    ) -> None:
        """Add labels to an issue or PR.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue or PR number
            labels: Labels to add
        """
        ...

    @abstractmethod
    def dispatch_workflow(
        self,
        *,
        owner: str,
        repo: str,
        workflow: str,
        ref: str,
        inputs: dict[str, str],
    ) -> str:
        """Dispatch a workflow and poll for the run ID.

        Args:
            owner: Repository owner
            repo: Repository name
            workflow: Workflow filename (e.g., "one-shot.yml")
            ref: Git ref to dispatch from
            inputs: Workflow input parameters

        Returns:
            Workflow run ID string
        """
        ...

    @abstractmethod
    def add_issue_comment(
        self,
        *,
        owner: str,
        repo: str,
        issue_number: int,
        body: str,
    ) -> None:
        """Add a comment to an issue or PR.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue or PR number
            body: Comment body
        """
        ...

    # --- Read operations for PR commands ---

    @abstractmethod
    def get_issue(
        self,
        *,
        owner: str,
        repo: str,
        number: int,
    ) -> IssueInfo | IssueNotFound:
        """Fetch issue data by number.

        Args:
            owner: Repository owner
            repo: Repository name
            number: Issue number to fetch

        Returns:
            IssueInfo if found, IssueNotFound if not
        """
        ...

    @abstractmethod
    def get_issue_comments(
        self,
        *,
        owner: str,
        repo: str,
        number: int,
    ) -> list[str]:
        """Fetch all comment bodies for an issue.

        Args:
            owner: Repository owner
            repo: Repository name
            number: Issue number

        Returns:
            List of comment body strings
        """
        ...

    @abstractmethod
    def list_issues(
        self,
        *,
        owner: str,
        repo: str,
        labels: tuple[str, ...],
        state: str,
        limit: int | None,
        creator: str | None,
    ) -> list[IssueInfo]:
        """List issues with filtering.

        Args:
            owner: Repository owner
            repo: Repository name
            labels: Labels to filter by
            state: Issue state ("open" or "closed")
            limit: Maximum number of issues (None for no limit)
            creator: Filter by creator username (None for all)

        Returns:
            List of IssueInfo objects
        """
        ...

    @abstractmethod
    def get_prs_referencing_issue(
        self,
        *,
        owner: str,
        repo: str,
        number: int,
    ) -> list[PRReference]:
        """Get PRs that reference an issue via timeline API.

        Args:
            owner: Repository owner
            repo: Repository name
            number: Issue number

        Returns:
            List of PRReference objects
        """
        ...

    @abstractmethod
    def close_issue(
        self,
        *,
        owner: str,
        repo: str,
        number: int,
    ) -> None:
        """Close a GitHub issue.

        Args:
            owner: Repository owner
            repo: Repository name
            number: Issue number to close
        """
        ...

    @abstractmethod
    def close_pr(
        self,
        *,
        owner: str,
        repo: str,
        number: int,
    ) -> None:
        """Close a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            number: PR number to close
        """
        ...

    @abstractmethod
    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Check authentication status via REST API.

        Returns:
            Tuple of (is_authenticated, username, error_message)
        """
        ...
