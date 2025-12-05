"""No-op GitBranches wrapper for dry-run mode."""

from pathlib import Path

from erk_shared.git.branches.abc import GitBranches
from erk_shared.output.output import user_output


class DryRunGitBranches(GitBranches):
    """No-op wrapper that prevents execution of destructive operations."""

    def __init__(self, wrapped: GitBranches) -> None:
        self._wrapped = wrapped

    # Read-only: delegate
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

    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        return self._wrapped.branch_exists_on_remote(repo_root, remote, branch)

    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        return self._wrapped.get_branch_head(repo_root, branch)

    # Write operations: no-op or print dry-run message
    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        pass  # No-op

    def create_branch(self, cwd: Path, branch_name: str, start_point: str) -> None:
        user_output(f"[DRY RUN] Would run: git branch {branch_name} {start_point}")

    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        flag = "-D" if force else "-d"
        user_output(f"[DRY RUN] Would run: git branch {flag} {branch_name}")

    def delete_branch_with_graphite(self, repo_root: Path, branch: str, *, force: bool) -> None:
        force_flag = "-f " if force else ""
        user_output(f"[DRY RUN] Would run: gt delete {force_flag}{branch}")

    def checkout_branch(self, cwd: Path, branch: str) -> None:
        pass  # No-op

    def checkout_detached(self, cwd: Path, ref: str) -> None:
        pass  # No-op
