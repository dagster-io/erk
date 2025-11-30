"""Production Git implementation using subprocess.

This module provides the real Git implementation that executes actual git
commands via subprocess. Located in erk-shared so it can be used by both
the main erk package and dot-agent-kit without circular dependencies.
"""

import os
import re
import subprocess
from pathlib import Path

from erk_shared.git.abc import BranchSyncInfo, Git, WorktreeInfo
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGit(Git):
    """Production implementation using subprocess.

    All git operations execute actual git commands via subprocess.
    """

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

    def get_current_branch(self, cwd: Path) -> str | None:
        """Get the currently checked-out branch."""
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None

        branch = result.stdout.strip()
        if branch == "HEAD":
            return None

        return branch

    def detect_default_branch(self, repo_root: Path, configured: str | None = None) -> str:
        """Detect the default branch (main or master)."""
        # If trunk is explicitly configured, validate and use it
        if configured is not None:
            result = subprocess.run(
                ["git", "rev-parse", "--verify", configured],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return configured
            error_msg = (
                f"Error: Configured trunk branch '{configured}' does not exist in repository.\n"
                f"Update your configuration in pyproject.toml or create the branch."
            )
            raise RuntimeError(error_msg)

        # Auto-detection: try remote HEAD first
        result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            remote_head = result.stdout.strip()
            if remote_head.startswith("refs/remotes/origin/"):
                branch = remote_head.replace("refs/remotes/origin/", "")
                return branch

        # Fallback: check master first, then main
        for candidate in ["master", "main"]:
            result = subprocess.run(
                ["git", "rev-parse", "--verify", candidate],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return candidate

        raise RuntimeError("Error: Could not find 'main' or 'master' branch.")

    def get_trunk_branch(self, repo_root: Path) -> str:
        """Get the trunk branch name for the repository.

        Detects trunk by checking git's remote HEAD reference. Falls back to
        checking for existence of common trunk branch names if detection fails.
        """
        # 1. Try git symbolic-ref to detect default branch
        result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            # Parse "refs/remotes/origin/master" -> "master"
            ref = result.stdout.strip()
            if ref.startswith("refs/remotes/origin/"):
                return ref.replace("refs/remotes/origin/", "")

        # 2. Fallback: try 'main' then 'master', use first that exists
        for candidate in ["main", "master"]:
            result = subprocess.run(
                ["git", "show-ref", "--verify", f"refs/heads/{candidate}"],
                cwd=repo_root,
                capture_output=True,
                check=False,
            )
            if result.returncode == 0:
                return candidate

        # 3. Final fallback: 'main'
        return "main"

    def list_local_branches(self, repo_root: Path) -> list[str]:
        """List all local branch names in the repository."""
        result = run_subprocess_with_context(
            ["git", "branch", "--format=%(refname:short)"],
            operation_context="list local branches",
            cwd=repo_root,
        )
        branches = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        return branches

    def list_remote_branches(self, repo_root: Path) -> list[str]:
        """List all remote branch names in the repository."""
        result = run_subprocess_with_context(
            ["git", "branch", "-r", "--format=%(refname:short)"],
            operation_context="list remote branches",
            cwd=repo_root,
        )
        return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]

    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        """Create a local tracking branch from a remote branch."""
        run_subprocess_with_context(
            ["git", "branch", "--track", branch, remote_ref],
            operation_context=f"create tracking branch '{branch}' from '{remote_ref}'",
            cwd=repo_root,
        )

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

    def has_staged_changes(self, repo_root: Path) -> bool:
        """Check if the repository has staged changes."""
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode in (0, 1):
            return result.returncode == 1
        result.check_returncode()
        return False

    def has_uncommitted_changes(self, cwd: Path) -> bool:
        """Check if a worktree has uncommitted changes."""
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False
        return bool(result.stdout.strip())

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
        # Exit code 0 means no changes, 1 means changes exist
        if result.returncode not in (0, 1):
            return False
        if result.returncode == 1:
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

    def checkout_branch(self, cwd: Path, branch: str) -> None:
        """Checkout a branch in the given directory."""
        run_subprocess_with_context(
            ["git", "checkout", branch],
            operation_context=f"checkout branch '{branch}'",
            cwd=cwd,
        )

    def checkout_detached(self, cwd: Path, ref: str) -> None:
        """Checkout a detached HEAD at the given ref."""
        run_subprocess_with_context(
            ["git", "checkout", "--detach", ref],
            operation_context=f"checkout detached HEAD at '{ref}'",
            cwd=cwd,
        )

    def create_branch(self, cwd: Path, branch_name: str, start_point: str) -> None:
        """Create a new branch without checking it out."""
        run_subprocess_with_context(
            ["git", "branch", branch_name, start_point],
            operation_context=f"create branch '{branch_name}' from '{start_point}'",
            cwd=cwd,
        )

    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        """Delete a local branch."""
        flag = "-D" if force else "-d"
        run_subprocess_with_context(
            ["git", "branch", flag, branch_name],
            operation_context=f"delete branch '{branch_name}'",
            cwd=cwd,
        )

    def delete_branch_with_graphite(self, repo_root: Path, branch: str, *, force: bool) -> None:
        """Delete a branch using Graphite's gt delete command."""
        cmd = ["gt", "delete", branch]
        if force:
            cmd.insert(2, "-f")
        run_subprocess_with_context(
            cmd,
            operation_context=f"delete branch '{branch}' with Graphite",
            cwd=repo_root,
        )

    def prune_worktrees(self, repo_root: Path) -> None:
        """Prune stale worktree metadata."""
        run_subprocess_with_context(
            ["git", "worktree", "prune"],
            operation_context="prune worktree metadata",
            cwd=repo_root,
        )

    def path_exists(self, path: Path) -> bool:
        """Check if a path exists on the filesystem."""
        return path.exists()

    def is_dir(self, path: Path) -> bool:
        """Check if a path is a directory."""
        return path.is_dir()

    def safe_chdir(self, path: Path) -> bool:
        """Change current directory if path exists on real filesystem."""
        if not path.exists():
            return False
        os.chdir(path)
        return True

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

    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        """Get the commit SHA at the head of a branch."""
        result = subprocess.run(
            ["git", "rev-parse", branch],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None

        return result.stdout.strip()

    def get_commit_message(self, repo_root: Path, commit_sha: str) -> str | None:
        """Get the first line of commit message for a given commit SHA."""
        result = subprocess.run(
            ["git", "log", "-1", "--format=%s", commit_sha],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None

        return result.stdout.strip()

    def get_file_status(self, cwd: Path) -> tuple[list[str], list[str], list[str]]:
        """Get lists of staged, modified, and untracked files."""
        result = run_subprocess_with_context(
            ["git", "status", "--porcelain"],
            operation_context="get file status",
            cwd=cwd,
        )

        staged = []
        modified = []
        untracked = []

        for line in result.stdout.splitlines():
            if not line:
                continue

            status_code = line[:2]
            filename = line[3:]

            # Check if file is staged (first character is not space)
            if status_code[0] != " " and status_code[0] != "?":
                staged.append(filename)

            # Check if file is modified (second character is not space)
            if status_code[1] != " " and status_code[1] != "?":
                modified.append(filename)

            # Check if file is untracked
            if status_code == "??":
                untracked.append(filename)

        return staged, modified, untracked

    def get_ahead_behind(self, cwd: Path, branch: str) -> tuple[int, int]:
        """Get number of commits ahead and behind tracking branch."""
        # Check if branch has upstream
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            # No upstream branch
            return 0, 0

        upstream = result.stdout.strip()

        # Get ahead/behind counts
        result = run_subprocess_with_context(
            ["git", "rev-list", "--left-right", "--count", f"{upstream}...HEAD"],
            operation_context=f"get ahead/behind counts for branch '{branch}'",
            cwd=cwd,
        )

        parts = result.stdout.strip().split()
        if len(parts) == 2:
            behind = int(parts[0])
            ahead = int(parts[1])
            return ahead, behind

        return 0, 0

    def get_all_branch_sync_info(self, repo_root: Path) -> dict[str, BranchSyncInfo]:
        """Get sync status for all local branches via git for-each-ref."""
        result = subprocess.run(
            [
                "git",
                "for-each-ref",
                "--format=%(refname:short)\t%(upstream:short)\t%(upstream:track)",
                "refs/heads/",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return {}

        sync_info: dict[str, BranchSyncInfo] = {}
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            branch = parts[0]
            upstream = parts[1] if len(parts) > 1 and parts[1] else None
            track = parts[2] if len(parts) > 2 else ""

            ahead, behind = 0, 0
            if track:
                # Parse "[ahead N, behind M]" or "[ahead N]" or "[behind M]"
                ahead_match = re.search(r"ahead (\d+)", track)
                behind_match = re.search(r"behind (\d+)", track)
                if ahead_match:
                    ahead = int(ahead_match.group(1))
                if behind_match:
                    behind = int(behind_match.group(1))

            sync_info[branch] = BranchSyncInfo(
                branch=branch,
                upstream=upstream,
                ahead=ahead,
                behind=behind,
            )

        return sync_info

    def get_recent_commits(self, cwd: Path, *, limit: int = 5) -> list[dict[str, str]]:
        """Get recent commit information."""
        result = run_subprocess_with_context(
            [
                "git",
                "log",
                f"-{limit}",
                "--format=%H%x00%s%x00%an%x00%ar",
            ],
            operation_context=f"get recent {limit} commits",
            cwd=cwd,
        )

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("\x00")
            if len(parts) == 4:
                commits.append(
                    {
                        "sha": parts[0][:7],  # Short SHA
                        "message": parts[1],
                        "author": parts[2],
                        "date": parts[3],
                    }
                )

        return commits

    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        """Fetch a specific branch from a remote."""
        run_subprocess_with_context(
            ["git", "fetch", remote, branch],
            operation_context=f"fetch branch '{branch}' from remote '{remote}'",
            cwd=repo_root,
        )

    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        """Pull a specific branch from a remote."""
        cmd = ["git", "pull"]
        if ff_only:
            cmd.append("--ff-only")
        cmd.extend([remote, branch])

        run_subprocess_with_context(
            cmd,
            operation_context=f"pull branch '{branch}' from remote '{remote}'",
            cwd=repo_root,
        )

    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        """Check if a branch exists on a remote."""
        result = subprocess.run(
            ["git", "ls-remote", remote, branch],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        return bool(result.stdout.strip())

    def set_branch_issue(self, repo_root: Path, branch: str, issue_number: int) -> None:
        """Associate a GitHub issue number with a branch via git config."""
        run_subprocess_with_context(
            ["git", "config", f"branch.{branch}.issue", str(issue_number)],
            operation_context=f"set issue #{issue_number} for branch '{branch}'",
            cwd=repo_root,
        )

    def get_branch_issue(self, repo_root: Path, branch: str) -> int | None:
        """Get GitHub issue number associated with a branch from git config.

        Note: Uses subprocess exception handling as an acceptable error boundary.
        We cannot check if the config key exists beforehandwithout duplicating
        git's logic.
        """
        result = subprocess.run(
            ["git", "config", f"branch.{branch}.issue"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,  # LBYL: check return code after
        )

        # Check if config key exists
        if result.returncode != 0:
            return None

        # Parse issue number from output
        try:
            return int(result.stdout.strip())
        except ValueError:
            # Config value exists but is not a valid integer
            return None

    def fetch_pr_ref(self, repo_root: Path, remote: str, pr_number: int, local_branch: str) -> None:
        """Fetch a PR ref into a local branch.

        Uses GitHub's special refs/pull/<number>/head reference.
        """
        run_subprocess_with_context(
            ["git", "fetch", remote, f"pull/{pr_number}/head:{local_branch}"],
            operation_context=f"fetch PR #{pr_number} into branch '{local_branch}'",
            cwd=repo_root,
        )

    def stage_files(self, cwd: Path, paths: list[str]) -> None:
        """Stage specific files for commit."""
        run_subprocess_with_context(
            ["git", "add", *paths],
            operation_context=f"stage files: {', '.join(paths)}",
            cwd=cwd,
        )

    def commit(self, cwd: Path, message: str, *, allow_empty: bool = False) -> None:
        """Create a commit with staged changes."""
        cmd = ["git", "commit", "-m", message]
        if allow_empty:
            cmd.append("--allow-empty")
        run_subprocess_with_context(
            cmd,
            operation_context="create commit",
            cwd=cwd,
        )

    def push_to_remote(
        self, cwd: Path, remote: str, branch: str, *, set_upstream: bool = False
    ) -> None:
        """Push a branch to a remote."""
        cmd = ["git", "push"]
        if set_upstream:
            cmd.append("-u")
        cmd.extend([remote, branch])

        run_subprocess_with_context(
            cmd,
            operation_context=f"push branch '{branch}' to remote '{remote}'",
            cwd=cwd,
        )
