"""GraphiteDisabled sentinel for when Graphite is not available.

This module provides a sentinel implementation of the Graphite ABC that
raises helpful errors on mutating operations while allowing read-only
operations to return empty/no-op results.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from erk_shared.gateway.graphite.abc import Graphite
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.git.abc import Git
from erk_shared.github.types import GitHubRepoId, PullRequestInfo


class GraphiteDisabledReason(Enum):
    """Reason why Graphite is disabled."""

    CONFIG_DISABLED = "config_disabled"
    NOT_INSTALLED = "not_installed"


class GraphiteDisabledError(Exception):
    """Raised when attempting mutating Graphite operations while disabled."""

    def __init__(self, reason: GraphiteDisabledReason) -> None:
        self.reason = reason
        if reason == GraphiteDisabledReason.CONFIG_DISABLED:
            message = (
                "This command requires Graphite to be enabled.\n\n"
                "To enable Graphite integration:\n"
                "  erk config set use_graphite true"
            )
        else:
            message = (
                "This command requires Graphite to be installed.\n\n"
                "Install Graphite CLI:\n"
                "  npm install -g @withgraphite/graphite-cli\n\n"
                "Then enable Graphite in erk:\n"
                "  erk config set use_graphite true"
            )
        super().__init__(message)


@dataclass(frozen=True)
class GraphiteDisabled(Graphite):
    """Sentinel implementation of Graphite for when it's unavailable.

    Read-only methods return empty/no-op results.
    Mutating methods raise GraphiteDisabledError with helpful messages.

    The get_graphite_url() method always works since it's pure string
    construction with no external dependencies.
    """

    reason: GraphiteDisabledReason

    def get_graphite_url(self, repo_id: GitHubRepoId, pr_number: int) -> str:
        """Get Graphite PR URL - always works (pure string construction)."""
        return f"https://app.graphite.dev/github/pr/{repo_id.owner}/{repo_id.repo}/{pr_number}"

    def sync(self, repo_root: Path, *, force: bool, quiet: bool) -> None:
        """Raise error - sync is a mutating operation."""
        raise GraphiteDisabledError(self.reason)

    def restack(self, repo_root: Path, *, no_interactive: bool, quiet: bool) -> None:
        """Raise error - restack is a mutating operation."""
        raise GraphiteDisabledError(self.reason)

    def get_prs_from_graphite(self, git_ops: Git, repo_root: Path) -> dict[str, PullRequestInfo]:
        """Return empty dict - no PR info available when disabled."""
        return {}

    def get_all_branches(self, git_ops: Git, repo_root: Path) -> dict[str, BranchMetadata]:
        """Return empty dict - no branch metadata when disabled."""
        return {}

    def get_branch_stack(self, git_ops: Git, repo_root: Path, branch: str) -> list[str] | None:
        """Return None - branch not tracked when disabled."""
        return None

    def track_branch(self, cwd: Path, branch_name: str, parent_branch: str) -> None:
        """Raise error - track_branch is a mutating operation."""
        raise GraphiteDisabledError(self.reason)

    def submit_branch(self, repo_root: Path, branch_name: str, *, quiet: bool) -> None:
        """Raise error - submit_branch is a mutating operation."""
        raise GraphiteDisabledError(self.reason)

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Return not authenticated - auth not applicable when disabled."""
        return (False, None, None)

    def squash_branch(self, repo_root: Path, *, quiet: bool = False) -> None:
        """Raise error - squash_branch is a mutating operation."""
        raise GraphiteDisabledError(self.reason)

    def submit_stack(
        self,
        repo_root: Path,
        *,
        publish: bool = False,
        restack: bool = False,
        quiet: bool = False,
        force: bool = False,
    ) -> None:
        """Raise error - submit_stack is a mutating operation."""
        raise GraphiteDisabledError(self.reason)

    def is_branch_tracked(self, repo_root: Path, branch: str) -> bool:
        """Return False - no branches tracked when disabled."""
        return False

    def continue_restack(self, repo_root: Path, *, quiet: bool = False) -> None:
        """Raise error - continue_restack is a mutating operation."""
        raise GraphiteDisabledError(self.reason)

    def delete_branch(self, repo_root: Path, branch: str) -> None:
        """Raise error - delete_branch is a mutating operation."""
        raise GraphiteDisabledError(self.reason)
