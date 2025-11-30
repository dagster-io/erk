"""Type definitions for GitHub operations."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, NamedTuple

PRState = Literal["OPEN", "MERGED", "CLOSED", "NONE"]


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
    labels: list[str] = field(default_factory=list)  # PR labels (e.g., ["erk-plan"])
    checks_counts: tuple[int, int] | None = None  # (passing, total) or None if no checks


@dataclass(frozen=True)
class PRMergeability:
    """GitHub PR mergeability status."""

    mergeable: str  # "MERGEABLE", "CONFLICTING", "UNKNOWN"
    merge_state_status: str  # "CLEAN", "BLOCKED", "UNSTABLE", "DIRTY", etc.


@dataclass(frozen=True)
class WorkflowRun:
    """Information about a GitHub Actions workflow run."""

    run_id: str
    status: str  # "in_progress", "completed", "queued"
    conclusion: str | None  # "success", "failure", "cancelled" (None if in progress)
    branch: str
    head_sha: str
    display_title: str | None = None  # The display title (e.g., issue title for dispatch workflows)
    created_at: datetime | None = None  # Timestamp when the workflow run was created (UTC)


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
