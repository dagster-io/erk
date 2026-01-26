"""No-op Graphite branch operations wrapper for dry-run mode."""

from pathlib import Path

from erk_shared.gateway.graphite.branch_ops.abc import GraphiteBranchOps


class DryRunGraphiteBranchOps(GraphiteBranchOps):
    """No-op wrapper that prevents execution of branch operations.

    This wrapper intercepts branch operations and returns without
    executing (no-op behavior).

    Usage:
        real_ops = RealGraphiteBranchOps()
        noop_ops = DryRunGraphiteBranchOps(real_ops)

        # No-op instead of tracking branch
        noop_ops.track_branch(cwd, "feature", "main")
    """

    def __init__(self, wrapped: GraphiteBranchOps) -> None:
        """Create a dry-run wrapper around a GraphiteBranchOps implementation.

        Args:
            wrapped: The GraphiteBranchOps implementation to wrap
        """
        self._wrapped = wrapped

    def track_branch(self, cwd: Path, branch_name: str, parent_branch: str) -> None:
        """No-op for gt track in dry-run mode."""
        # Do nothing - prevents actual gt track execution
        pass

    def delete_branch(self, repo_root: Path, branch: str) -> None:
        """No-op for gt delete in dry-run mode."""
        # Do nothing - prevents actual gt delete execution
        pass

    def submit_branch(self, repo_root: Path, branch_name: str, *, quiet: bool) -> None:
        """No-op for gt submit in dry-run mode."""
        # Do nothing - prevents actual gt submit execution
        pass

    def retrack_branch(self, cwd: Path, branch_name: str) -> None:
        """No-op for gt track (re-track) in dry-run mode."""
        # Do nothing - prevents actual gt track execution
        pass
