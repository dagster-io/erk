"""Production worktree implementation using subprocess.

This module provides the real worktree implementation that executes actual git
worktree commands via subprocess.
"""

import os
import subprocess
from pathlib import Path

from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.worktree.abc import Worktree
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealWorktree(Worktree):
    """Production implementation using subprocess.

    All worktree operations execute actual git commands via subprocess.
    """

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """List all worktrees in the repository."""
        result = run_subprocess_with_context(
            cmd=["git", "worktree", "list", "--porcelain"],
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

        run_subprocess_with_context(cmd=cmd, operation_context=context, cwd=repo_root)

    def move_worktree(self, repo_root: Path, old_path: Path, new_path: Path) -> None:
        """Move a worktree to a new location."""
        cmd = ["git", "worktree", "move", str(old_path), str(new_path)]
        run_subprocess_with_context(
            cmd=cmd,
            operation_context=f"move worktree from {old_path} to {new_path}",
            cwd=repo_root,
        )

    def remove_worktree(self, repo_root: Path, path: Path, *, force: bool) -> None:
        """Remove a worktree."""
        # Find the main git directory BEFORE deleting the worktree
        # This handles the case where repo_root IS the worktree being deleted
        main_git_dir = self._find_main_git_dir(repo_root)

        cmd = ["git", "worktree", "remove"]
        if force:
            cmd.append("--force")
        cmd.append(str(path))
        run_subprocess_with_context(
            cmd=cmd,
            operation_context=f"remove worktree at {path}",
            cwd=repo_root,
        )

        # Clean up git worktree metadata to prevent permission issues during test cleanup
        # This prunes stale administrative files left behind after worktree removal
        # Use main_git_dir for prune - repo_root may have been deleted
        run_subprocess_with_context(
            cmd=["git", "worktree", "prune"],
            operation_context="prune worktree metadata",
            cwd=main_git_dir,
        )

    def _find_main_git_dir(self, repo_root: Path) -> Path:
        """Find the main repository root (where .git directory lives).

        For worktrees, this resolves the actual git directory location.
        For main repos, returns repo_root unchanged.
        """
        result = run_subprocess_with_context(
            cmd=["git", "rev-parse", "--git-common-dir"],
            operation_context="find main git directory",
            cwd=repo_root,
        )
        git_common_dir = Path(result.stdout.strip())

        # Handle relative paths - git may return relative path
        if not git_common_dir.is_absolute():
            git_common_dir = (repo_root / git_common_dir).resolve()

        # --git-common-dir returns the .git directory, we want its parent
        if git_common_dir.name == ".git":
            return git_common_dir.parent
        # For bare repos or unusual setups, just return parent
        return git_common_dir.parent

    def prune_worktrees(self, repo_root: Path) -> None:
        """Prune stale worktree metadata."""
        run_subprocess_with_context(
            cmd=["git", "worktree", "prune"],
            operation_context="prune worktree metadata",
            cwd=repo_root,
        )

    def find_worktree_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        """Find worktree path for given branch name."""
        worktrees = self.list_worktrees(repo_root)
        for wt in worktrees:
            if wt.branch == branch:
                return wt.path
        return None

    def is_branch_checked_out(self, repo_root: Path, branch: str) -> Path | None:
        """Check if a branch is already checked out in any worktree."""
        return self.find_worktree_for_branch(repo_root, branch)

    def is_worktree_clean(self, worktree_path: Path) -> bool:
        """Check if worktree has no uncommitted changes, staged changes, or untracked files."""
        # LBYL: Check path exists before attempting git operations
        if not worktree_path.exists():
            return False

        # Check for uncommitted changes using diff-index (respects git config)
        result = subprocess.run(
            ["git", "-C", str(worktree_path), "diff-index", "--quiet", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        # Exit code 0 means no changes, non-zero means changes exist or error
        if result.returncode != 0:
            return False

        # Check for untracked files
        result = subprocess.run(
            ["git", "-C", str(worktree_path), "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False
        if result.stdout.strip():
            return False

        return True

    def safe_chdir(self, path: Path) -> bool:
        """Change current directory if path exists on real filesystem."""
        if not path.exists():
            return False
        os.chdir(path)
        return True

    def path_exists(self, path: Path) -> bool:
        """Check if a path exists on the filesystem."""
        return path.exists()

    def is_dir(self, path: Path) -> bool:
        """Check if a path is a directory."""
        return path.is_dir()
