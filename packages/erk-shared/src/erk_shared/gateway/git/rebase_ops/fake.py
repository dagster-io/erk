"""Fake implementation of Git rebase operations for testing."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from erk_shared.gateway.git.abc import RebaseResult
from erk_shared.gateway.git.rebase_ops.abc import GitRebaseOps


class FakeGitRebaseOps(GitRebaseOps):
    """In-memory fake implementation of Git rebase operations.

    This fake accepts pre-configured state in its constructor and tracks
    mutations for test assertions.

    Constructor Injection:
    ---------------------
    - rebase_in_progress: Initial state for is_rebase_in_progress() (bool or callable)
    - rebase_onto_result: Result to return from rebase_onto()
    - rebase_continue_raises: Exception to raise when rebase_continue() is called
    - rebase_continue_clears_rebase: If True, rebase_continue() clears rebase state
    - rebase_abort_raises: Exception to raise when rebase_abort() is called

    Mutation Tracking:
    -----------------
    This fake tracks mutations for test assertions via read-only properties:
    - rebase_onto_calls: List of (cwd, target_ref) tuples from rebase_onto()
    - rebase_continue_calls: List of cwd from rebase_continue()
    - rebase_abort_calls: List of cwd from rebase_abort()
    """

    def __init__(
        self,
        *,
        rebase_in_progress: bool | Callable[[Path], bool] | None = None,
        rebase_onto_result: RebaseResult | None = None,
        rebase_continue_raises: Exception | None = None,
        rebase_continue_clears_rebase: bool | None = None,
        rebase_abort_raises: Exception | None = None,
    ) -> None:
        """Create FakeGitRebaseOps with pre-configured state.

        Args:
            rebase_in_progress: Initial state for is_rebase_in_progress().
                Can be a bool or a callable(cwd) -> bool for dynamic behavior.
            rebase_onto_result: Result to return from rebase_onto()
            rebase_continue_raises: Exception to raise when rebase_continue() is called
            rebase_continue_clears_rebase: If True, rebase_continue() clears rebase state
            rebase_abort_raises: Exception to raise when rebase_abort() is called
        """
        # Handle rebase_in_progress as bool or callable
        if rebase_in_progress is None:
            self._rebase_in_progress: bool | None = False
            self._rebase_in_progress_callable: Callable[[Path], bool] | None = None
        elif callable(rebase_in_progress):
            self._rebase_in_progress = None
            self._rebase_in_progress_callable = rebase_in_progress
        else:
            self._rebase_in_progress = rebase_in_progress
            self._rebase_in_progress_callable = None

        self._rebase_onto_result = rebase_onto_result
        self._rebase_continue_raises = rebase_continue_raises
        self._rebase_continue_clears_rebase = (
            rebase_continue_clears_rebase if rebase_continue_clears_rebase is not None else False
        )
        self._rebase_abort_raises = rebase_abort_raises

        # Mutation tracking
        self._rebase_onto_calls: list[tuple[Path, str]] = []
        self._rebase_continue_calls: list[Path] = []
        self._rebase_abort_calls: list[Path] = []

    def rebase_onto(self, cwd: Path, target_ref: str) -> RebaseResult:
        """Rebase the current branch onto a target ref.

        Returns the configured rebase_onto_result if set, otherwise returns success.
        Tracks call for test assertions.
        """
        self._rebase_onto_calls.append((cwd, target_ref))
        if self._rebase_onto_result is not None:
            return self._rebase_onto_result
        return RebaseResult(success=True, conflict_files=())

    def rebase_continue(self, cwd: Path) -> None:
        """Continue an in-progress rebase.

        Tracks call for test assertions. Raises configured exception if set.
        Note: rebase_continue_clears_rebase only affects boolean state, not callables.
        """
        if self._rebase_continue_raises is not None:
            raise self._rebase_continue_raises
        self._rebase_continue_calls.append(cwd)
        if self._rebase_continue_clears_rebase and self._rebase_in_progress_callable is None:
            self._rebase_in_progress = False

    def rebase_abort(self, cwd: Path) -> None:
        """Abort an in-progress rebase operation.

        Tracks call for test assertions. Raises configured exception if set.
        """
        self._rebase_abort_calls.append(cwd)
        if self._rebase_abort_raises is not None:
            raise self._rebase_abort_raises

    def is_rebase_in_progress(self, cwd: Path) -> bool:
        """Check if a rebase is in progress.

        Returns the result of the callable if one was provided, otherwise
        returns the boolean state.
        """
        if self._rebase_in_progress_callable is not None:
            return self._rebase_in_progress_callable(cwd)
        # _rebase_in_progress is guaranteed to be bool when callable is None
        assert self._rebase_in_progress is not None
        return self._rebase_in_progress

    # ============================================================================
    # Mutation Tracking Properties
    # ============================================================================

    @property
    def rebase_onto_calls(self) -> list[tuple[Path, str]]:
        """Read-only access to rebase_onto calls for test assertions.

        Returns list of (cwd, target_ref) tuples.
        """
        return list(self._rebase_onto_calls)

    @property
    def rebase_continue_calls(self) -> list[Path]:
        """Read-only access to rebase_continue calls for test assertions.

        Returns list of cwd paths.
        """
        return list(self._rebase_continue_calls)

    @property
    def rebase_abort_calls(self) -> list[Path]:
        """Read-only access to rebase_abort calls for test assertions.

        Returns list of cwd paths.
        """
        return list(self._rebase_abort_calls)

    # ============================================================================
    # Link Mutation Tracking (for integration with FakeGit)
    # ============================================================================

    def link_mutation_tracking(
        self,
        *,
        rebase_onto_calls: list[tuple[Path, str]],
        rebase_continue_calls: list[Path],
        rebase_abort_calls: list[Path],
    ) -> None:
        """Link this fake's mutation tracking to FakeGit's tracking lists.

        This allows FakeGit to expose rebase operations mutations through its
        own properties while delegating to this subgateway.

        Args:
            rebase_onto_calls: FakeGit's _rebase_onto_calls list
            rebase_continue_calls: FakeGit's _rebase_continue_calls list
            rebase_abort_calls: FakeGit's _rebase_abort_calls list
        """
        self._rebase_onto_calls = rebase_onto_calls
        self._rebase_continue_calls = rebase_continue_calls
        self._rebase_abort_calls = rebase_abort_calls

    def link_state(
        self,
        *,
        get_rebase_in_progress: Callable,
        set_rebase_in_progress: Callable,
    ) -> None:
        """Link rebase state to FakeGit's state.

        This allows FakeGit to share rebase-in-progress state with this subgateway.

        Args:
            get_rebase_in_progress: Function returning current rebase state
            set_rebase_in_progress: Function to update rebase state
        """
        self._get_rebase_in_progress = get_rebase_in_progress
        self._set_rebase_in_progress = set_rebase_in_progress
