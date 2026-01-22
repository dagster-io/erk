"""Production implementation of Graphite branch operations using subprocess."""

import subprocess
import sys
from pathlib import Path
from subprocess import DEVNULL

from erk_shared.gateway.graphite.branch_ops.abc import GraphiteBranchOps
from erk_shared.output.output import user_output
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGraphiteBranchOps(GraphiteBranchOps):
    """Production implementation of branch operations using gt CLI.

    All gt operations execute actual gt commands via subprocess.
    """

    def __init__(self) -> None:
        """Initialize RealGraphiteBranchOps."""
        # This class maintains no state; cache management (if any) would be
        # handled by the caller or a coordinator
        pass

    def track_branch(self, cwd: Path, branch_name: str, parent_branch: str) -> None:
        """Track a branch with Graphite.

        Uses `gt track --branch <branch> --parent <parent>` to register a branch
        in Graphite's cache.

        Args:
            cwd: Working directory where gt track should run
            branch_name: Name of the branch to track
            parent_branch: Name of the parent branch in the stack
        """
        run_subprocess_with_context(
            cmd=["gt", "track", "--branch", branch_name, "--parent", parent_branch],
            operation_context=f"track branch '{branch_name}' with Graphite",
            cwd=cwd,
        )

    def delete_branch(self, repo_root: Path, branch: str) -> None:
        """Delete a branch using Graphite's gt delete command."""
        run_subprocess_with_context(
            cmd=["gt", "delete", "-f", branch],
            operation_context=f"delete branch '{branch}' with Graphite",
            cwd=repo_root,
        )

    def submit_branch(self, repo_root: Path, branch_name: str, *, quiet: bool) -> None:
        """Submit (force-push) a branch to GitHub.

        Uses `gt submit --branch <branch> --no-edit` to push a branch that was
        rebased by `gt sync -f`. This ensures GitHub PRs show the rebased commits
        rather than stale versions with duplicate commits.

        Error output (stderr) is always captured to ensure RuntimeError
        includes complete error messages for debugging. In verbose mode (!quiet),
        stderr is displayed to the user after successful execution.

        Args:
            repo_root: Repository root directory
            branch_name: Name of the branch to submit
            quiet: If True, pass --quiet flag to gt submit for minimal output
        """
        cmd = ["gt", "submit", "--branch", branch_name, "--no-edit", "--no-interactive"]
        if quiet:
            cmd.append("--quiet")

        result = run_subprocess_with_context(
            cmd=cmd,
            operation_context=f"submit branch '{branch_name}' with Graphite",
            cwd=repo_root,
            stdout=DEVNULL if quiet else sys.stdout,
            stderr=subprocess.PIPE,
        )

        # Display stderr in verbose mode after successful execution
        if not quiet and result.stderr:
            user_output(result.stderr, nl=False)
