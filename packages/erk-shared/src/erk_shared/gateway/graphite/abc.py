"""Abstract base class for Graphite operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from erk_shared.gateway.git.abc import Git, WorktreeInfo
from erk_shared.gateway.github.types import GitHubRepoId, PullRequestInfo
from erk_shared.gateway.graphite.types import BranchMetadata

if TYPE_CHECKING:
    from erk_shared.gateway.gt.types import RestackError, RestackSuccess, SquashError, SquashSuccess


class Graphite(ABC):
    """Abstract interface for Graphite operations.

    All implementations (real and fake) must implement this interface.
    """

    @abstractmethod
    def get_graphite_url(self, repo_id: GitHubRepoId, pr_number: int) -> str:
        """Get Graphite PR URL for a pull request.

        Args:
            repo_id: GitHub repository identity (owner and repo name)
            pr_number: GitHub PR number

        Returns:
            Graphite PR URL (e.g., "https://app.graphite.com/github/pr/dagster-io/erk/23")
        """
        ...

    @abstractmethod
    def sync(self, repo_root: Path, *, force: bool, quiet: bool) -> None:
        """Run gt sync to synchronize with remote.

        Args:
            repo_root: Repository root directory
            force: If True, pass --force flag to gt sync
            quiet: If True, pass --quiet flag to gt sync for minimal output
        """
        ...

    @abstractmethod
    def restack(self, repo_root: Path, *, no_interactive: bool, quiet: bool) -> None:
        """Run gt restack to rebase the current stack.

        This is more surgical than sync - it only affects the current stack,
        not all branches in the repository. Safe to use in non-interactive
        mode during automated workflows.

        Args:
            repo_root: Repository root directory
            no_interactive: If True, pass --no-interactive flag to prevent prompts
            quiet: If True, pass --quiet flag to gt restack for minimal output
        """
        ...

    @abstractmethod
    def get_prs_from_graphite(self, git_ops: Git, repo_root: Path) -> dict[str, PullRequestInfo]:
        """Get PR information from Graphite's local cache.

        Reads .git/.graphite_pr_info and returns PR data in the same format
        as GitHub.get_prs_for_repo() for compatibility.

        Args:
            git_ops: Git instance for accessing git common directory
            repo_root: Repository root directory

        Returns:
            Mapping of branch name -> PullRequestInfo
            - checks_passing is always None (CI status not available)
            - Empty dict if .graphite_pr_info doesn't exist
        """
        ...

    @abstractmethod
    def get_all_branches(self, git_ops: Git, repo_root: Path) -> dict[str, BranchMetadata]:
        """Get all gt-tracked branches with metadata.

        Reads .git/.graphite_cache_persist and returns branch relationship data
        along with current commit SHAs from git.

        Args:
            git_ops: Git instance for accessing git common directory and branch heads
            repo_root: Repository root directory

        Returns:
            Mapping of branch name -> BranchMetadata
            Empty dict if:
            - .graphite_cache_persist doesn't exist
            - Git common directory cannot be determined
        """
        ...

    @abstractmethod
    def get_branch_stack(self, git_ops: Git, repo_root: Path, branch: str) -> list[str] | None:
        """Get the linear worktree stack for a given branch.

        This function builds the linear chain of branches that the given branch belongs to.
        The chain includes:
        - All ancestor branches from current down to trunk
        - All descendant branches from current up to the leaf

        Args:
            git_ops: Git instance for accessing git common directory and branch heads
            repo_root: Repository root directory
            branch: Name of the branch to get the stack for

        Returns:
            List of branch names in the stack, ordered from trunk to leaf
            (e.g., ["main", "feature-1", "feature-2", "feature-3"]).
            Returns None if branch is not tracked by graphite
        """
        ...

    @abstractmethod
    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Check Graphite authentication status.

        Runs `gt auth` and parses the output to determine authentication status.
        This is a LBYL check to validate Graphite authentication before operations
        that require it (like gt submit).

        Returns:
            Tuple of (is_authenticated, username, repo_info):
            - is_authenticated: True if gt is authenticated
            - username: Authenticated username (e.g., "schrockn") or None if not authenticated
            - repo_info: Repository info string (e.g., "dagster-io/erk") or None

        Example:
            >>> graphite.check_auth_status()
            (True, "schrockn", "dagster-io/erk")
            >>> # If not authenticated:
            (False, None, None)
        """
        ...

    @abstractmethod
    def squash_branch(self, repo_root: Path, *, quiet: bool = False) -> None:
        """Squash all commits on the current branch into one.

        Uses `gt squash` to consolidate commits. This is typically called
        before submitting a PR to create a clean single-commit branch.

        Args:
            repo_root: Repository root directory
            quiet: If True, suppress output

        Raises:
            RuntimeError: If gt squash fails
        """
        ...

    @abstractmethod
    def submit_stack(
        self,
        repo_root: Path,
        *,
        publish: bool = False,
        restack: bool = False,
        quiet: bool = False,
        force: bool = False,
    ) -> None:
        """Submit the current stack to create or update PRs.

        Uses `gt submit` to push branches and create/update GitHub PRs.
        This differs from submit_branch() which only pushes a single branch
        without PR creation.

        Args:
            repo_root: Repository root directory
            publish: If True, mark PRs as ready for review (not draft)
            restack: If True, restack before submitting
            quiet: If True, suppress output
            force: If True, force push (useful after squashing commits)

        Raises:
            RuntimeError: If gt submit fails or times out
        """
        ...

    def get_parent_branch(self, git_ops: Git, repo_root: Path, branch: str) -> str | None:
        """Get parent branch name for a given branch.

        This is a convenience helper that calls get_all_branches() and extracts
        the parent relationship. All implementations inherit this method.

        Args:
            git_ops: Git instance for accessing git common directory
            repo_root: Repository root directory
            branch: Name of the branch to get the parent for

        Returns:
            Parent branch name, or None if:
            - Branch is not tracked by graphite
            - Branch has no parent (is trunk)
        """
        all_branches = self.get_all_branches(git_ops, repo_root)
        if branch not in all_branches:
            return None
        return all_branches[branch].parent

    def get_child_branches(self, git_ops: Git, repo_root: Path, branch: str) -> list[str]:
        """Get child branch names for a given branch.

        This is a convenience helper that calls get_all_branches() and extracts
        the children relationship. All implementations inherit this method.

        Args:
            git_ops: Git instance for accessing git common directory
            repo_root: Repository root directory
            branch: Name of the branch to get children for

        Returns:
            List of child branch names, or empty list if:
            - Branch is not tracked by graphite
            - Branch has no children
        """
        all_branches = self.get_all_branches(git_ops, repo_root)
        if branch not in all_branches:
            return []
        return all_branches[branch].children

    def find_ancestor_worktree(
        self,
        git_ops: Git,
        repo_root: Path,
        branch: str,
    ) -> WorktreeInfo | None:
        """Find the worktree of the closest ancestor branch.

        Walks up the Graphite parent chain to find the first ancestor
        that has a worktree checked out. This is a composing template method
        that uses get_parent_branch() to traverse the branch hierarchy.

        Args:
            git_ops: Git instance for worktree listing and git common directory
            repo_root: Repository root directory
            branch: Branch name to find ancestor worktree for

        Returns:
            WorktreeInfo of the closest ancestor with a worktree, or None if
            no ancestor has a worktree (reaches trunk without finding one).

        Raises:
            ValueError: If branch is not tracked by Graphite (indicates caller bug).
        """
        # Validate branch exists in Graphite - if not, it's a caller bug
        all_branches = self.get_all_branches(git_ops, repo_root)
        if branch not in all_branches:
            raise ValueError(f"Branch '{branch}' is not tracked by Graphite")

        worktrees = git_ops.worktree.list_worktrees(repo_root)
        current = branch
        while True:
            parent = self.get_parent_branch(git_ops, repo_root, current)
            if parent is None:
                break

            for wt in worktrees:
                if wt.branch == parent:
                    return wt

            current = parent

        return None

    @abstractmethod
    def is_branch_tracked(self, repo_root: Path, branch: str) -> bool:
        """Check if a branch is tracked by Graphite.

        Uses `gt branch info` to get authoritative tracking status from the gt CLI.
        This is a LBYL check to verify tracking status before operations that
        require a tracked branch (like gt delete).

        Args:
            repo_root: Repository root directory
            branch: Name of the branch to check

        Returns:
            True if branch is tracked by Graphite, False if untracked or gt reports error.
        """
        ...

    def is_branch_diverged_from_tracking(self, git_ops: Git, repo_root: Path, branch: str) -> bool:
        """Check if branch is diverged from Graphite's tracked SHA.

        Compares Graphite's cached branchRevision with actual git HEAD.
        Returns True if they differ (branch needs re-tracking).

        This happens when gt restack or other operations create new commit SHAs
        without updating Graphite's internal tracking. The branch is "diverged"
        from Graphite's perspective, which can cause gt track on child branches
        to fail with "Cannot perform this operation on diverged branch."

        Args:
            git_ops: Git instance for accessing git common directory and branch heads
            repo_root: Repository root directory
            branch: Name of the branch to check

        Returns:
            True if branch is diverged (tracked_revision != commit_sha),
            False if not diverged or branch is not tracked.
        """
        branches = self.get_all_branches(git_ops, repo_root)
        if branch not in branches:
            return False  # Not tracked = not diverged

        metadata = branches[branch]

        # If we don't have tracking info, assume not diverged
        if metadata.tracked_revision is None or metadata.commit_sha is None:
            return False

        return metadata.tracked_revision != metadata.commit_sha

    @abstractmethod
    def continue_restack(self, repo_root: Path, *, quiet: bool = False) -> None:
        """Continue an in-progress gt restack (gt continue).

        This is used after manually resolving merge conflicts during a restack
        operation. The gt continue command tells Graphite to proceed with the
        rebase using the resolved files.

        Args:
            repo_root: Repository root directory
            quiet: If True, suppress output

        Raises:
            subprocess.CalledProcessError: If continue fails (e.g., unresolved conflicts)
        """
        ...

    def squash_branch_idempotent(
        self, repo_root: Path, *, quiet: bool = True
    ) -> SquashSuccess | SquashError:
        """Squash commits idempotently - succeeds even if already single commit.

        This is a convenience method that wraps squash_branch() and handles the
        common case where git's commit count (against trunk) differs from
        Graphite's view (against parent branch). When Graphite reports "nothing
        to squash", this is treated as success rather than an error.

        This composites the primitive squash_branch() operation with error
        handling to provide a more ergonomic API for callers who don't need
        to distinguish between "squashed N commits" and "already single commit".

        Args:
            repo_root: Repository root directory
            quiet: If True, suppress output from gt squash

        Returns:
            SquashSuccess if squash succeeded or was unnecessary
            SquashError if squash failed (conflict or other error)

        Example:
            >>> result = graphite.squash_branch_idempotent(repo_root)
            >>> if result.success:
            ...     print(result.message)  # "Squashed commits" or "Already single commit"
            >>> else:
            ...     print(f"Error: {result.message}")
        """
        import subprocess

        # Import at runtime to avoid circular dependency
        from erk_shared.gateway.gt.types import SquashError, SquashSuccess

        try:
            self.squash_branch(repo_root, quiet=quiet)
            return SquashSuccess(
                success=True,
                action="squashed",
                commit_count=1,  # After squash, always 1 commit
                message="Squashed commits into 1.",
            )
        except (RuntimeError, subprocess.CalledProcessError) as e:
            # Build error message from exception
            # RuntimeError: from run_subprocess_with_context (real implementation)
            # CalledProcessError: from FakeGraphite (test implementation)
            if isinstance(e, subprocess.CalledProcessError):
                error_msg = (
                    (e.stderr if hasattr(e, "stderr") and e.stderr else "")
                    + (e.stdout if hasattr(e, "stdout") and e.stdout else "")
                ).lower()
            else:
                error_msg = str(e).lower()

            # "nothing to squash" means Graphite sees only 1 commit.
            # This is success - the branch is already in the desired state.
            if "nothing to squash" in error_msg:
                return SquashSuccess(
                    success=True,
                    action="already-single-commit",
                    commit_count=1,
                    message="Already a single commit, no squash needed.",
                )
            if "conflict" in error_msg:
                return SquashError(
                    success=False,
                    error="squash-conflict",
                    message="Merge conflicts detected during squash.",
                )
            return SquashError(
                success=False,
                error="squash-failed",
                message=f"Failed to squash: {e}",
            )

    def restack_idempotent(
        self, repo_root: Path, *, no_interactive: bool, quiet: bool
    ) -> RestackSuccess | RestackError:
        """Restack with structured result handling.

        This method wraps restack() and handles exceptions to return a typed
        result instead of raising. It encapsulates the exception-to-result
        conversion at the gateway boundary, keeping CLI code LBYL-compliant.

        This method catches RuntimeError from restack() and parses the error
        message to detect conflict patterns. While parsing exception messages
        is inherently fragile, this pattern is acceptable because:
        1. It's encapsulated in the gateway layer (not CLI code)
        2. The Graphite CLI doesn't provide structured error codes
        3. False negatives (treating conflicts as generic errors) are safe

        Args:
            repo_root: Repository root directory
            no_interactive: If True, pass --no-interactive flag to prevent prompts
            quiet: If True, pass --quiet flag to gt restack for minimal output

        Returns:
            RestackSuccess if restack succeeded
            RestackError if restack failed (with error_type distinguishing conflicts)

        Example:
            >>> result = graphite.restack_idempotent(repo_root, no_interactive=True, quiet=False)
            >>> if isinstance(result, RestackSuccess):
            ...     print(result.message)
            >>> elif result.error_type == "restack-conflict":
            ...     print("Resolve conflicts and run: gt continue")
        """
        # Import at runtime to avoid circular dependency
        from erk_shared.gateway.gt.types import RestackError, RestackSuccess

        try:
            self.restack(repo_root, no_interactive=no_interactive, quiet=quiet)
            return RestackSuccess(
                success=True,
                message="Branch restacked.",
            )
        except RuntimeError as e:
            error_msg = str(e).lower()

            # Detect conflict patterns from gt restack stderr
            if "conflict" in error_msg or "unmerged files" in error_msg:
                return RestackError(
                    success=False,
                    error_type="restack-conflict",
                    message=str(e),
                )
            return RestackError(
                success=False,
                error_type="restack-failed",
                message=f"Failed to restack: {e}",
            )
