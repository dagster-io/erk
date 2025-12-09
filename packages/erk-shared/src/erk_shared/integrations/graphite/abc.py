"""Abstract base class for Graphite operations."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from erk_shared.git.abc import Git
from erk_shared.github.types import GitHubRepoId, PullRequestInfo
from erk_shared.integrations.graphite.types import BranchMetadata

if TYPE_CHECKING:
    from erk_shared.integrations.gt.types import SquashError, SquashSuccess


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
    def track_branch(self, cwd: Path, branch_name: str, parent_branch: str) -> None:
        """Track a branch with Graphite.

        Uses `gt track` to register a branch in Graphite's cache. This is needed
        when branches are created with direct git operations (git branch) instead
        of gt create.

        Args:
            cwd: Working directory where gt track should run
            branch_name: Name of the branch to track
            parent_branch: Name of the parent branch in the stack
        """
        ...

    @abstractmethod
    def submit_branch(self, repo_root: Path, branch_name: str, *, quiet: bool) -> None:
        """Submit (force-push) a branch to GitHub.

        Uses `gt submit` to push a branch that was rebased by `gt sync -f`.
        This is typically called after merging a PR to push the rebased remaining
        branches in a stack to GitHub.

        Args:
            repo_root: Repository root directory
            branch_name: Name of the branch to submit
            quiet: If True, pass --quiet flag to gt submit for minimal output
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
    ) -> "SquashSuccess | SquashError":
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
        from erk_shared.integrations.gt.types import SquashError, SquashSuccess

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
                    action="already_single_commit",
                    commit_count=1,
                    message="Already a single commit, no squash needed.",
                )
            if "conflict" in error_msg:
                return SquashError(
                    success=False,
                    error="squash_conflict",
                    message="Merge conflicts detected during squash.",
                )
            return SquashError(
                success=False,
                error="squash_failed",
                message=f"Failed to squash: {e}",
            )
