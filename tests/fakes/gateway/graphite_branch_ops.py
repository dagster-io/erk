"""Fake Graphite branch operations for testing."""

from __future__ import annotations

from pathlib import Path

from erk_shared.gateway.graphite.branch_ops.abc import GraphiteBranchOps


class FakeGraphiteBranchOps(GraphiteBranchOps):
    """In-memory fake implementation of Graphite branch operations.

    State Management:
    -----------------
    This fake maintains mutable state to simulate Graphite's stateful behavior.
    Operations like track_branch modify internal state.
    State changes are visible to subsequent method calls within the same test.

    Mutation Tracking:
    -----------------
    This fake tracks mutations for test assertions via read-only properties:
    - track_branch_calls: Branches tracked via track_branch()
    - delete_branch_calls: Branches deleted via delete_branch()
    - submit_branch_calls: Branches submitted via submit_branch()
    - retrack_branch_calls: Branches re-tracked via retrack_branch()
    """

    def __init__(
        self,
        *,
        track_branch_raises: Exception | None = None,
        delete_branch_raises: Exception | None = None,
        submit_branch_raises: Exception | None = None,
        retrack_branch_raises: Exception | None = None,
        tracked_branches: set[str] | None = None,
    ) -> None:
        """Create FakeGraphiteBranchOps with pre-configured state.

        Args:
            track_branch_raises: Exception to raise when track_branch() is called
            delete_branch_raises: Exception to raise when delete_branch() is called
            submit_branch_raises: Exception to raise when submit_branch() is called
            retrack_branch_raises: Exception to raise when retrack_branch() is called
            tracked_branches: Set of branches that are "tracked" by Graphite
        """
        self._track_branch_raises = track_branch_raises
        self._delete_branch_raises = delete_branch_raises
        self._submit_branch_raises = submit_branch_raises
        self._retrack_branch_raises = retrack_branch_raises
        self._tracked_branches = tracked_branches if tracked_branches is not None else set()

        # Mutation tracking
        self._track_branch_calls: list[tuple[Path, str, str]] = []
        self._delete_branch_calls: list[tuple[Path, str]] = []
        self._submit_branch_calls: list[tuple[Path, str, bool]] = []
        self._retrack_branch_calls: list[tuple[Path, str]] = []

    def track_branch(self, cwd: Path, branch_name: str, parent_branch: str) -> None:
        """Track a branch with Graphite (fake implementation).

        Tracks the call and optionally raises configured exception.
        """
        self._track_branch_calls.append((cwd, branch_name, parent_branch))
        self._tracked_branches.add(branch_name)

        if self._track_branch_raises is not None:
            raise self._track_branch_raises

    def delete_branch(self, repo_root: Path, branch: str) -> None:
        """Delete a branch (fake implementation).

        Tracks the call and optionally raises configured exception.
        """
        self._delete_branch_calls.append((repo_root, branch))
        self._tracked_branches.discard(branch)

        if self._delete_branch_raises is not None:
            raise self._delete_branch_raises

    def submit_branch(self, repo_root: Path, branch_name: str, *, quiet: bool) -> None:
        """Submit a branch (fake implementation).

        Tracks the call and optionally raises configured exception.
        """
        self._submit_branch_calls.append((repo_root, branch_name, quiet))

        if self._submit_branch_raises is not None:
            raise self._submit_branch_raises

    def retrack_branch(self, cwd: Path, branch_name: str) -> None:
        """Re-track a branch (fake implementation).

        Tracks the call and optionally raises configured exception.
        """
        self._retrack_branch_calls.append((cwd, branch_name))

        if self._retrack_branch_raises is not None:
            raise self._retrack_branch_raises

    @property
    def track_branch_calls(self) -> list[tuple[Path, str, str]]:
        """Get list of track_branch() calls for test assertions.

        Returns list of (cwd, branch_name, parent_branch) tuples.
        """
        return self._track_branch_calls.copy()

    @property
    def delete_branch_calls(self) -> list[tuple[Path, str]]:
        """Get list of delete_branch() calls for test assertions.

        Returns list of (repo_root, branch) tuples.
        """
        return self._delete_branch_calls.copy()

    @property
    def submit_branch_calls(self) -> list[tuple[Path, str, bool]]:
        """Get list of submit_branch() calls for test assertions.

        Returns list of (repo_root, branch_name, quiet) tuples.
        """
        return self._submit_branch_calls.copy()

    @property
    def retrack_branch_calls(self) -> list[tuple[Path, str]]:
        """Get list of retrack_branch() calls for test assertions.

        Returns list of (cwd, branch_name) tuples.
        """
        return self._retrack_branch_calls.copy()

    def is_branch_tracked(self, branch: str) -> bool:
        """Check if a branch is tracked (for test setup).

        Note: This is a helper method not in the ABC; useful for test validation.
        """
        return branch in self._tracked_branches

    def link_state_from_graphite(self, tracked_branches: set[str]) -> None:
        """Link mutable state from FakeGraphite to keep in sync.

        This allows FakeGraphiteBranchOps to operate on the same state as FakeGraphite
        when both are used together.

        Args:
            tracked_branches: Reference to FakeGraphite's tracked branches set
        """
        self._tracked_branches = tracked_branches

    def link_mutation_tracking(
        self,
        *,
        track_branch_calls: list[tuple[Path, str, str]],
        delete_branch_calls: list[tuple[Path, str]],
        submit_branch_calls: list[tuple[Path, str, bool]],
        retrack_branch_calls: list[tuple[Path, str]] | None = None,
    ) -> None:
        """Link mutation tracking lists to allow shared tracking with FakeGraphite.

        This allows FakeGraphite.track_branch_calls (etc.) to see mutations made
        via FakeGraphiteBranchOps when used via BranchManager.

        Args:
            track_branch_calls: Reference to FakeGraphite's track_branch_calls list
            delete_branch_calls: Reference to FakeGraphite's delete_branch_calls list
            submit_branch_calls: Reference to FakeGraphite's submit_branch_calls list
            retrack_branch_calls: Reference to FakeGraphite's retrack_branch_calls list
        """
        self._track_branch_calls = track_branch_calls
        self._delete_branch_calls = delete_branch_calls
        self._submit_branch_calls = submit_branch_calls
        if retrack_branch_calls is not None:
            self._retrack_branch_calls = retrack_branch_calls
