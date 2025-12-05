"""Production GitWorktrees implementation using subprocess."""

import subprocess
from pathlib import Path

from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.worktrees.abc import GitWorktrees
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitWorktrees(GitWorktrees):
    """Production implementation using subprocess."""

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """List all worktrees in the repository."""
        result = run_subprocess_with_context(
            ["git", "worktree", "list", "--porcelain"],
            operation_context="list worktrees",
            cwd=repo_root,
        )

        worktrees: list[WorktreeInfo] = []
        current_path: Path | None = None
        current_branch: str | None = None

        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("worktree "):
                current_path = Path(line.split(maxsplit=1)[1])
                current_branch = None
            elif line.startswith("branch "):
                if current_path is None:
                    continue
                branch_ref = line.split(maxsplit=1)[1]
                current_branch = branch_ref.replace("refs/heads/", "")
            elif line == "" and current_path is not None:
                worktrees.append(WorktreeInfo(path=current_path, branch=current_branch))
                current_path = None
                current_branch = None

        if current_path is not None:
            worktrees.append(WorktreeInfo(path=current_path, branch=current_branch))

        # Mark first worktree as root (git guarantees this ordering)
        if worktrees:
            first = worktrees[0]
            worktrees[0] = WorktreeInfo(path=first.path, branch=first.branch, is_root=True)

        return worktrees

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get the common git directory."""
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None

        git_dir = Path(result.stdout.strip())
        if not git_dir.is_absolute():
            git_dir = cwd / git_dir

        return git_dir.resolve()

    def add_worktree(
        self,
        repo_root: Path,
        path: Path,
        *,
        branch: str | None,
        ref: str | None,
        create_branch: bool,
    ) -> None:
        """Add a new git worktree."""
        if branch and not create_branch:
            cmd = ["git", "worktree", "add", str(path), branch]
            context = f"add worktree for branch '{branch}' at {path}"
        elif branch and create_branch:
            base_ref = ref or "HEAD"
            cmd = ["git", "worktree", "add", "-b", branch, str(path), base_ref]
            context = f"add worktree with new branch '{branch}' at {path}"
        else:
            base_ref = ref or "HEAD"
            cmd = ["git", "worktree", "add", str(path), base_ref]
            context = f"add worktree at {path}"

        run_subprocess_with_context(cmd, operation_context=context, cwd=repo_root)

    def move_worktree(self, repo_root: Path, old_path: Path, new_path: Path) -> None:
        """Move a worktree to a new location."""
        cmd = ["git", "worktree", "move", str(old_path), str(new_path)]
        run_subprocess_with_context(
            cmd,
            operation_context=f"move worktree from {old_path} to {new_path}",
            cwd=repo_root,
        )

    def remove_worktree(self, repo_root: Path, path: Path, *, force: bool) -> None:
        """Remove a worktree."""
        cmd = ["git", "worktree", "remove"]
        if force:
            cmd.append("--force")
        cmd.append(str(path))
        run_subprocess_with_context(
            cmd,
            operation_context=f"remove worktree at {path}",
            cwd=repo_root,
        )

        # Clean up git worktree metadata to prevent permission issues during test cleanup
        # This prunes stale administrative files left behind after worktree removal
        run_subprocess_with_context(
            ["git", "worktree", "prune"],
            operation_context="prune worktree metadata",
            cwd=repo_root,
        )

    def prune_worktrees(self, repo_root: Path) -> None:
        """Prune stale worktree metadata."""
        run_subprocess_with_context(
            ["git", "worktree", "prune"],
            operation_context="prune worktree metadata",
            cwd=repo_root,
        )

    def is_branch_checked_out(self, repo_root: Path, branch: str) -> Path | None:
        """Check if a branch is already checked out in any worktree."""
        worktrees = self.list_worktrees(repo_root)
        for wt in worktrees:
            if wt.branch == branch:
                return wt.path
        return None

    def find_worktree_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        """Find worktree path for given branch name."""
        worktrees = self.list_worktrees(repo_root)
        for wt in worktrees:
            if wt.branch == branch:
                return wt.path
        return None
