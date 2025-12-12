"""WtStack - Worktree stack operations with Graphite optionality.

WtStack is a thin orchestration layer that makes Graphite optionality transparent.
Instead of scattering "is Graphite available?" checks throughout the codebase,
WtStack handles this internally:

    - Queries return None/empty when Graphite is unavailable (graceful degradation)
    - Safe mutations no-op when unavailable
    - Unsafe mutations raise clearly (caller chooses by checking `is_available`)

Why not guards everywhere?
    Easy to forget. WtStack makes optionality the default behavior.

Why not absorb business logic?
    WtStack is minimal orchestration only. Business logic stays in operations layer.
    It composes Git + Graphite primitives but doesn't make business decisions.

Migration Work Items (ordered simplest -> complex):
=============================================================================

Work Item 1: get_parent() migration [SIMPLEST]
    Migrate: ctx.graphite.get_parent_branch(ctx.git, repo.root, branch)
    To:      ctx.wt_stack.get_parent(branch)
    Files:   navigation_helpers.py, sync_cmd.py, create_cmd.py

Work Item 2: get_children() migration
    Similar to get_parent, clear semantics
    Files:   navigation_helpers.py, land_cmd.py, up.py

Work Item 3: get_stack() migration
    Files:   stack/list_cmd.py, stack/consolidate_cmd.py, checkout.py

Work Item 4: is_tracked() + track() migration
    Track operations used in worktree creation and checkout
    Files:   create_cmd.py, checkout.py, consolidate_cmd.py

Work Item 5: get_all_branches() migration
    Used for branch metadata lookup
    Files:   create_cmd.py, checkout.py, graphite_enhance.py

Work Item 6: get_prs() migration
    PR info from Graphite cache
    Files:   wt/list_cmd.py, github.py collector

Work Item 7: Worktree operations (list_worktrees, find_worktree)
    Pure Git delegation, but included for API consistency
    Many call sites, but straightforward delegation

Work Item 8: Stack mutations (submit_stack, submit_branch, etc.) [MOST COMPLEX]
    Used in PR submission workflows
    Files:   graphite_enhance.py, sync_cmd.py, auto_restack_cmd.py

Work Item 9: Context integration
    Add wt_stack: WtStack to ErkContext, wire up in create_context()

Work Item 10: Deprecate direct ctx.graphite usage
    Eventually remove, leaving only ctx.wt_stack.graphite escape hatch
=============================================================================
"""

from pathlib import Path

from erk_shared.git.abc import Git, WorktreeInfo
from erk_shared.github.types import PullRequestInfo
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.graphite.types import BranchMetadata
from erk_shared.integrations.gt.types import SquashError, SquashSuccess


class GraphiteUnavailableError(Exception):
    """Raised when an operation requires Graphite but it's not available.

    Callers should check `wt_stack.is_available` before calling unsafe mutations,
    or handle this exception at error boundaries.
    """

    def __init__(self, operation: str) -> None:
        super().__init__(
            f"Cannot perform '{operation}': Graphite is not available. "
            f"Install Graphite or use a fallback workflow."
        )
        self.operation = operation


class WtStack:
    """Worktree stack operations with internal Graphite availability handling.

    Composes Git + Graphite and handles availability internally:
    - Queries return None/empty when Graphite is None
    - Safe mutations no-op when Graphite is None
    - Unsafe mutations raise GraphiteUnavailableError when Graphite is None
    - Worktree operations always work (pure Git delegation)

    For testing, inject FakeGit and FakeGraphite. The same class handles both
    "Graphite available" and "Graphite unavailable" scenarios based on whether
    graphite is None.
    """

    def __init__(self, git: Git, repo_root: Path, graphite: Graphite | None = None) -> None:
        """Initialize WtStack.

        Args:
            git: Git operations interface
            repo_root: Repository root path
            graphite: Graphite operations interface, or None if unavailable
        """
        self._git = git
        self._repo_root = repo_root
        self._graphite = graphite

    @property
    def is_available(self) -> bool:
        """Check if Graphite is available."""
        return self._graphite is not None

    @property
    def graphite(self) -> Graphite:
        """Return the underlying Graphite instance.

        Raises:
            GraphiteUnavailableError: If Graphite is not available
        """
        if self._graphite is None:
            raise GraphiteUnavailableError("graphite property access")
        return self._graphite

    # =========================================================================
    # Stack Queries - return None/empty when Graphite unavailable
    # Methods raise NotImplementedError until migrated
    # =========================================================================

    def get_parent(self, branch: str) -> str | None:
        """Get parent branch name. Returns None if unavailable or not tracked."""
        raise NotImplementedError("WtStack.get_parent - migrate Work Item 1")

    def get_children(self, branch: str) -> list[str]:
        """Get child branches. Returns [] if unavailable or not tracked."""
        raise NotImplementedError("WtStack.get_children - migrate Work Item 2")

    def get_stack(self, branch: str) -> list[str] | None:
        """Get full stack for branch. Returns None if unavailable or not tracked."""
        raise NotImplementedError("WtStack.get_stack - migrate Work Item 3")

    def is_tracked(self, branch: str) -> bool:
        """Check if branch is tracked by Graphite. Returns False if unavailable."""
        raise NotImplementedError("WtStack.is_tracked - migrate Work Item 4")

    def get_all_branches(self) -> dict[str, BranchMetadata]:
        """Get all tracked branches. Returns {} if unavailable."""
        raise NotImplementedError("WtStack.get_all_branches - migrate Work Item 5")

    def get_prs(self) -> dict[str, PullRequestInfo]:
        """Get PR info from Graphite cache. Returns {} if unavailable."""
        raise NotImplementedError("WtStack.get_prs - migrate Work Item 6")

    # =========================================================================
    # Safe Mutations - no-op when Graphite unavailable
    # =========================================================================

    def track(self, branch: str, parent: str) -> None:
        """Track branch with Graphite. No-op if unavailable."""
        raise NotImplementedError("WtStack.track - migrate Work Item 4")

    # =========================================================================
    # Unsafe Mutations - raise when Graphite unavailable
    # =========================================================================

    def submit_stack(
        self,
        *,
        publish: bool = False,
        restack: bool = False,
        quiet: bool = False,
        force: bool = False,
    ) -> None:
        """Submit stack to create/update PRs. Raises if unavailable."""
        raise NotImplementedError("WtStack.submit_stack - migrate Work Item 8")

    def submit_branch(self, branch: str, *, quiet: bool = False) -> None:
        """Submit specific branch. Raises if unavailable."""
        raise NotImplementedError("WtStack.submit_branch - migrate Work Item 8")

    def squash(self, *, quiet: bool = True) -> SquashSuccess | SquashError:
        """Squash commits idempotently. Raises if unavailable."""
        raise NotImplementedError("WtStack.squash - migrate Work Item 8")

    def sync(self, *, force: bool = False, quiet: bool = False) -> None:
        """Sync with remote. Raises if unavailable."""
        raise NotImplementedError("WtStack.sync - migrate Work Item 8")

    def restack(self, *, no_interactive: bool = False, quiet: bool = False) -> None:
        """Restack current stack. Raises if unavailable."""
        raise NotImplementedError("WtStack.restack - migrate Work Item 8")

    def continue_restack(self, *, quiet: bool = False) -> None:
        """Continue in-progress restack. Raises if unavailable."""
        raise NotImplementedError("WtStack.continue_restack - migrate Work Item 8")

    # =========================================================================
    # Worktree Operations - always work (pure Git delegation)
    # =========================================================================

    def list_worktrees(self) -> list[WorktreeInfo]:
        """List all worktrees. Always works."""
        raise NotImplementedError("WtStack.list_worktrees - migrate Work Item 7")

    def find_worktree(self, branch: str) -> Path | None:
        """Find worktree for branch. Always works."""
        raise NotImplementedError("WtStack.find_worktree - migrate Work Item 7")
