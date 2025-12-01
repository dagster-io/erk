"""Type definitions for GitHub operations."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, NamedTuple

PRState = Literal["OPEN", "MERGED", "CLOSED", "NONE"]

# Workflow run status (lowercase, matches gh CLI and normalized GraphQL responses)
WorkflowRunStatus = Literal["completed", "in_progress", "queued", "unknown"]

# Workflow run conclusion (lowercase, None when run is not completed)
WorkflowRunConclusion = Literal["success", "failure", "cancelled", "skipped"]


class PRInfo(NamedTuple):
    """PR status information from GitHub API."""

    state: PRState
    pr_number: int | None
    title: str | None


@dataclass(frozen=True)
class PullRequestInfo:
    """Information about a GitHub pull request."""

    number: int
    state: str  # "OPEN", "MERGED", "CLOSED"
    url: str
    is_draft: bool
    title: str | None
    checks_passing: bool | None  # None if no checks, True if all pass, False if any fail
    owner: str  # GitHub repo owner (e.g., "schrockn")
    repo: str  # GitHub repo name (e.g., "erk")
    # True if CONFLICTING, False if MERGEABLE, None if UNKNOWN or not fetched
    has_conflicts: bool | None = None
    checks_counts: tuple[int, int] | None = None  # (passing, total) or None if no checks


@dataclass(frozen=True)
class PRMergeability:
    """GitHub PR mergeability status."""

    mergeable: str  # "MERGEABLE", "CONFLICTING", "UNKNOWN"
    merge_state_status: str  # "CLEAN", "BLOCKED", "UNSTABLE", "DIRTY", etc.


class _NotAvailable:
    """Sentinel for fields not available from certain API queries.

    Raises AttributeError when accessed as a string, preventing silent bugs
    when code tries to use fields that weren't populated.
    """

    def __init__(self, field_name: str, source: str) -> None:
        self._field_name = field_name
        self._source = source

    def __str__(self) -> str:
        msg = f"'{self._field_name}' is not available from {self._source}"
        raise AttributeError(msg)

    def __repr__(self) -> str:
        return f"<NotAvailable: {self._field_name}>"

    def __eq__(self, other: object) -> bool:
        # Allow comparison with other _NotAvailable instances
        if isinstance(other, _NotAvailable):
            return self._field_name == other._field_name
        # Comparing with anything else (including strings) raises
        msg = f"'{self._field_name}' is not available from {self._source}"
        raise AttributeError(msg)

    def __hash__(self) -> int:
        return hash(("_NotAvailable", self._field_name))


# Sentinel instances for WorkflowRun fields not available from nodes() query
BRANCH_NOT_AVAILABLE = _NotAvailable("branch", "GraphQL nodes() query")
DISPLAY_TITLE_NOT_AVAILABLE = _NotAvailable("display_title", "GraphQL nodes() query")


class WorkflowRun:
    """Information about a GitHub Actions workflow run.

    Immutable class representing workflow run data. Some fields may not be
    available depending on the API query used to fetch the data:

    - branch: Not available from GraphQL nodes() query
    - display_title: Not available from GraphQL nodes() query

    Accessing unavailable fields raises AttributeError.
    """

    __slots__ = (
        "_run_id",
        "_status",
        "_conclusion",
        "_branch",
        "_head_sha",
        "_display_title",
        "_created_at",
    )

    _run_id: str
    _status: WorkflowRunStatus
    _conclusion: WorkflowRunConclusion | None
    _branch: str | _NotAvailable
    _head_sha: str
    _display_title: str | None | _NotAvailable
    _created_at: datetime | None

    def __init__(
        self,
        run_id: str,
        status: WorkflowRunStatus,
        conclusion: WorkflowRunConclusion | None,
        branch: str | _NotAvailable,
        head_sha: str,
        display_title: str | None | _NotAvailable = None,
        created_at: datetime | None = None,
    ) -> None:
        object.__setattr__(self, "_run_id", run_id)
        object.__setattr__(self, "_status", status)
        object.__setattr__(self, "_conclusion", conclusion)
        object.__setattr__(self, "_branch", branch)
        object.__setattr__(self, "_head_sha", head_sha)
        object.__setattr__(self, "_display_title", display_title)
        object.__setattr__(self, "_created_at", created_at)

    def __setattr__(self, name: str, value: object) -> None:
        msg = "WorkflowRun is immutable"
        raise AttributeError(msg)

    def __delattr__(self, name: str) -> None:
        msg = "WorkflowRun is immutable"
        raise AttributeError(msg)

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def status(self) -> WorkflowRunStatus:
        return self._status

    @property
    def conclusion(self) -> WorkflowRunConclusion | None:
        return self._conclusion

    @property
    def branch(self) -> str:
        value = self._branch
        if isinstance(value, _NotAvailable):
            str(value)  # Trigger the error
        return value  # type: ignore[return-value]

    @property
    def head_sha(self) -> str:
        return self._head_sha

    @property
    def display_title(self) -> str | None:
        value = self._display_title
        if isinstance(value, _NotAvailable):
            str(value)  # Trigger the error
        return value  # type: ignore[return-value]

    @property
    def created_at(self) -> datetime | None:
        return self._created_at

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WorkflowRun):
            return NotImplemented
        return (
            self._run_id == other._run_id
            and self._status == other._status
            and self._conclusion == other._conclusion
            and self._head_sha == other._head_sha
            and self._created_at == other._created_at
        )

    def __hash__(self) -> int:
        return hash((self._run_id, self._status, self._conclusion, self._head_sha))

    def __repr__(self) -> str:
        return (
            f"WorkflowRun(run_id={self._run_id!r}, status={self._status!r}, "
            f"conclusion={self._conclusion!r}, head_sha={self._head_sha!r})"
        )


@dataclass(frozen=True)
class PRCheckoutInfo:
    """Information needed to checkout a PR into a worktree.

    This dataclass contains the minimal information required to:
    1. Determine the local branch name to use
    2. Decide whether to fetch from GitHub's special PR ref
    3. Warn users about closed/merged PRs
    """

    number: int
    head_ref_name: str  # Branch name in source repo
    is_cross_repository: bool  # True if from a fork
    state: str  # OPEN, CLOSED, MERGED
