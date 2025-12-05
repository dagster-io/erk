"""Printing GitBranches wrapper for verbose output."""

from pathlib import Path

from erk_shared.git.branches.abc import GitBranches
from erk_shared.printing.base import PrintingBase


class PrintingGitBranches(PrintingBase, GitBranches):
    """Wrapper that prints operations before delegating."""

    # Read-only: delegate without printing
    def get_current_branch(self, cwd: Path) -> str | None:
        return self._wrapped.get_current_branch(cwd)

    def detect_trunk_branch(self, repo_root: Path) -> str:
        return self._wrapped.detect_trunk_branch(repo_root)

    def validate_trunk_branch(self, repo_root: Path, name: str) -> str:
        return self._wrapped.validate_trunk_branch(repo_root, name)

    def list_local_branches(self, repo_root: Path) -> list[str]:
        return self._wrapped.list_local_branches(repo_root)

    def list_remote_branches(self, repo_root: Path) -> list[str]:
        return self._wrapped.list_remote_branches(repo_root)

    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        return self._wrapped.get_branch_head(repo_root, branch)

    # Write operations: print then delegate
    def checkout_branch(self, cwd: Path, branch: str) -> None:
        self._emit(self._format_command(f"git checkout {branch}"))
        self._wrapped.checkout_branch(cwd, branch)

    def checkout_detached(self, cwd: Path, ref: str) -> None:
        self._wrapped.checkout_detached(cwd, ref)

    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        self._wrapped.create_tracking_branch(repo_root, branch, remote_ref)

    def create_branch(self, cwd: Path, branch_name: str, start_point: str) -> None:
        self._wrapped.create_branch(cwd, branch_name, start_point)

    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        self._wrapped.delete_branch(cwd, branch_name, force=force)

    def delete_branch_with_graphite(self, repo_root: Path, branch: str, *, force: bool) -> None:
        self._wrapped.delete_branch_with_graphite(repo_root, branch, force=force)
