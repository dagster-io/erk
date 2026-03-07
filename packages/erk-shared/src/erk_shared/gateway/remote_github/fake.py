"""Fake implementation of RemoteGitHub for testing.

Constructor-injected responses for reads, mutation tracking lists for write assertions.
"""

from dataclasses import dataclass

from erk_shared.gateway.remote_github.abc import RemoteGitHub


@dataclass(frozen=True)
class CreatedRef:
    """Recorded create_ref call."""

    owner: str
    repo: str
    ref: str
    sha: str


@dataclass(frozen=True)
class CreatedFileCommit:
    """Recorded create_file_commit call."""

    owner: str
    repo: str
    path: str
    content: str
    message: str
    branch: str


@dataclass(frozen=True)
class CreatedPullRequest:
    """Recorded create_pull_request call."""

    owner: str
    repo: str
    head: str
    base: str
    title: str
    body: str
    draft: bool


@dataclass(frozen=True)
class UpdatedPullRequestBody:
    """Recorded update_pull_request_body call."""

    owner: str
    repo: str
    pr_number: int
    body: str


@dataclass(frozen=True)
class AddedLabels:
    """Recorded add_labels call."""

    owner: str
    repo: str
    issue_number: int
    labels: tuple[str, ...]


@dataclass(frozen=True)
class DispatchedWorkflow:
    """Recorded dispatch_workflow call."""

    owner: str
    repo: str
    workflow: str
    ref: str
    inputs: dict[str, str]


@dataclass(frozen=True)
class AddedIssueComment:
    """Recorded add_issue_comment call."""

    owner: str
    repo: str
    issue_number: int
    body: str


class FakeRemoteGitHub(RemoteGitHub):
    """In-memory fake for testing remote GitHub operations.

    Constructor-injected values for reads, mutation tracking for writes.
    """

    def __init__(
        self,
        *,
        authenticated_user: str,
        default_branch_name: str,
        default_branch_sha: str,
        next_pr_number: int,
        dispatch_run_id: str,
    ) -> None:
        """Create FakeRemoteGitHub with configurable responses.

        Args:
            authenticated_user: Username to return from get_authenticated_user
            default_branch_name: Branch name to return from get_default_branch_name
            default_branch_sha: SHA to return from get_default_branch_sha
            next_pr_number: PR number to return from create_pull_request
            dispatch_run_id: Run ID to return from dispatch_workflow
        """
        self._authenticated_user = authenticated_user
        self._default_branch_name = default_branch_name
        self._default_branch_sha = default_branch_sha
        self._next_pr_number = next_pr_number
        self._dispatch_run_id = dispatch_run_id

        # Mutation tracking
        self._created_refs: list[CreatedRef] = []
        self._created_file_commits: list[CreatedFileCommit] = []
        self._created_pull_requests: list[CreatedPullRequest] = []
        self._updated_pr_bodies: list[UpdatedPullRequestBody] = []
        self._added_labels: list[AddedLabels] = []
        self._dispatched_workflows: list[DispatchedWorkflow] = []
        self._added_issue_comments: list[AddedIssueComment] = []

    # --- Read methods ---

    def get_authenticated_user(self) -> str:
        return self._authenticated_user

    def get_default_branch_name(self, *, owner: str, repo: str) -> str:
        return self._default_branch_name

    def get_default_branch_sha(self, *, owner: str, repo: str) -> str:
        return self._default_branch_sha

    # --- Write methods ---

    def create_ref(self, *, owner: str, repo: str, ref: str, sha: str) -> None:
        self._created_refs.append(CreatedRef(owner=owner, repo=repo, ref=ref, sha=sha))

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
        self._created_file_commits.append(
            CreatedFileCommit(
                owner=owner,
                repo=repo,
                path=path,
                content=content,
                message=message,
                branch=branch,
            )
        )
        return "fake-commit-sha"

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
        self._created_pull_requests.append(
            CreatedPullRequest(
                owner=owner,
                repo=repo,
                head=head,
                base=base,
                title=title,
                body=body,
                draft=draft,
            )
        )
        return self._next_pr_number

    def update_pull_request_body(
        self,
        *,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
    ) -> None:
        self._updated_pr_bodies.append(
            UpdatedPullRequestBody(owner=owner, repo=repo, pr_number=pr_number, body=body)
        )

    def add_labels(
        self,
        *,
        owner: str,
        repo: str,
        issue_number: int,
        labels: tuple[str, ...],
    ) -> None:
        self._added_labels.append(
            AddedLabels(owner=owner, repo=repo, issue_number=issue_number, labels=labels)
        )

    def dispatch_workflow(
        self,
        *,
        owner: str,
        repo: str,
        workflow: str,
        ref: str,
        inputs: dict[str, str],
    ) -> str:
        self._dispatched_workflows.append(
            DispatchedWorkflow(owner=owner, repo=repo, workflow=workflow, ref=ref, inputs=inputs)
        )
        return self._dispatch_run_id

    def add_issue_comment(
        self,
        *,
        owner: str,
        repo: str,
        issue_number: int,
        body: str,
    ) -> None:
        self._added_issue_comments.append(
            AddedIssueComment(owner=owner, repo=repo, issue_number=issue_number, body=body)
        )

    # --- Read-only properties for test assertions ---

    @property
    def created_refs(self) -> list[CreatedRef]:
        """Returns list of CreatedRef records."""
        return list(self._created_refs)

    @property
    def created_file_commits(self) -> list[CreatedFileCommit]:
        """Returns list of CreatedFileCommit records."""
        return list(self._created_file_commits)

    @property
    def created_pull_requests(self) -> list[CreatedPullRequest]:
        """Returns list of CreatedPullRequest records."""
        return list(self._created_pull_requests)

    @property
    def updated_pr_bodies(self) -> list[UpdatedPullRequestBody]:
        """Returns list of UpdatedPullRequestBody records."""
        return list(self._updated_pr_bodies)

    @property
    def added_labels(self) -> list[AddedLabels]:
        """Returns list of AddedLabels records."""
        return list(self._added_labels)

    @property
    def dispatched_workflows(self) -> list[DispatchedWorkflow]:
        """Returns list of DispatchedWorkflow records."""
        return list(self._dispatched_workflows)

    @property
    def added_issue_comments(self) -> list[AddedIssueComment]:
        """Returns list of AddedIssueComment records."""
        return list(self._added_issue_comments)
