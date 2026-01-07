"""Production Git implementation using subprocess.

This module provides the real Git implementation that executes actual git
commands via subprocess. Located in erk-shared so it can be used by both
the main erk package and erk-kits without circular dependencies.
"""

import os
import re
import subprocess
from pathlib import Path

from erk_shared.git.abc import BranchDivergence, BranchSyncInfo, Git, RebaseResult, WorktreeInfo
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGit(Git):
    """Production implementation using subprocess.

    All git operations execute actual git commands via subprocess.
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

    def detect_trunk_branch(self, repo_root: Path) -> str:
        """Auto-detect the trunk branch name.

        Checks git's remote HEAD reference, then falls back to checking for
        existence of 'main' then 'master'. Returns 'main' as final fallback
        if neither branch exists.
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

    def validate_trunk_branch(self, repo_root: Path, name: str) -> str:
        """Validate that a configured trunk branch exists.

        Args:
            repo_root: Path to the repository root
            name: Trunk branch name to validate

        Returns:
            The validated trunk branch name

        Raises:
            RuntimeError: If the specified branch doesn't exist
        """
        result = subprocess.run(
            ["git", "rev-parse", "--verify", name],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return name
        error_msg = (
            f"Error: Configured trunk branch '{name}' does not exist in repository.\n"
            f"Update your configuration in pyproject.toml or create the branch."
        )
        raise RuntimeError(error_msg)

    def list_local_branches(self, repo_root: Path) -> list[str]:
        """List all local branch names in the repository."""
        result = run_subprocess_with_context(
            cmd=["git", "branch", "--format=%(refname:short)"],
            operation_context="list local branches",
            cwd=repo_root,
        )
        branches = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        return branches

    def list_remote_branches(self, repo_root: Path) -> list[str]:
        """List all remote branch names in the repository."""
        result = run_subprocess_with_context(
            cmd=["git", "branch", "-r", "--format=%(refname:short)"],
            operation_context="list remote branches",
            cwd=repo_root,
        )
        return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]

    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        """Create a local tracking branch from a remote branch."""
        run_subprocess_with_context(
            cmd=["git", "branch", "--track", branch, remote_ref],
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

    def checkout_branch(self, cwd: Path, branch: str) -> None:
        """Checkout a branch in the given directory."""
        run_subprocess_with_context(
            cmd=["git", "checkout", branch],
            operation_context=f"checkout branch '{branch}'",
            cwd=cwd,
        )

    def checkout_detached(self, cwd: Path, ref: str) -> None:
        """Checkout a detached HEAD at the given ref."""
        run_subprocess_with_context(
            cmd=["git", "checkout", "--detach", ref],
            operation_context=f"checkout detached HEAD at '{ref}'",
            cwd=cwd,
        )

    def create_branch(self, cwd: Path, branch_name: str, start_point: str) -> None:
        """Create a new branch without checking it out."""
        run_subprocess_with_context(
            cmd=["git", "branch", branch_name, start_point],
            operation_context=f"create branch '{branch_name}' from '{start_point}'",
            cwd=cwd,
        )

    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        """Delete a local branch."""
        flag = "-D" if force else "-d"
        run_subprocess_with_context(
            cmd=["git", "branch", flag, branch_name],
            operation_context=f"delete branch '{branch_name}'",
            cwd=cwd,
        )

    def prune_worktrees(self, repo_root: Path) -> None:
        """Prune stale worktree metadata."""
        run_subprocess_with_context(
            cmd=["git", "worktree", "prune"],
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
            cmd=["git", "status", "--porcelain"],
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
            cmd=["git", "rev-list", "--left-right", "--count", f"{upstream}...HEAD"],
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
            cmd=[
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
            cmd=["git", "fetch", remote, branch],
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
            cmd=cmd,
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

    def get_branch_issue(self, repo_root: Path, branch: str) -> int | None:
        """Extract GitHub issue number from branch name.

        Branch names follow the pattern: P{issue_number}-{slug}-{timestamp}
        """
        from erk_shared.naming import extract_leading_issue_number

        return extract_leading_issue_number(branch)

    def fetch_pr_ref(
        self, *, repo_root: Path, remote: str, pr_number: int, local_branch: str
    ) -> None:
        """Fetch a PR ref into a local branch.

        Uses GitHub's special refs/pull/<number>/head reference.
        """
        run_subprocess_with_context(
            cmd=["git", "fetch", remote, f"pull/{pr_number}/head:{local_branch}"],
            operation_context=f"fetch PR #{pr_number} into branch '{local_branch}'",
            cwd=repo_root,
        )

    def stage_files(self, cwd: Path, paths: list[str]) -> None:
        """Stage specific files for commit."""
        run_subprocess_with_context(
            cmd=["git", "add", *paths],
            operation_context=f"stage files: {', '.join(paths)}",
            cwd=cwd,
        )

    def commit(self, cwd: Path, message: str) -> None:
        """Create a commit with staged changes."""
        run_subprocess_with_context(
            cmd=["git", "commit", "--allow-empty", "-m", message],
            operation_context="create commit",
            cwd=cwd,
        )

    def push_to_remote(
        self,
        cwd: Path,
        remote: str,
        branch: str,
        *,
        set_upstream: bool = False,
        force: bool = False,
    ) -> None:
        """Push a branch to a remote."""
        cmd = ["git", "push"]
        if set_upstream:
            cmd.append("-u")
        if force:
            cmd.append("--force")
        cmd.extend([remote, branch])

        run_subprocess_with_context(
            cmd=cmd,
            operation_context=f"push branch '{branch}' to remote '{remote}'",
            cwd=cwd,
        )

    def get_branch_last_commit_time(self, repo_root: Path, branch: str, trunk: str) -> str | None:
        """Get the author date of the most recent commit unique to a branch."""
        result = subprocess.run(
            ["git", "log", f"{trunk}..{branch}", "-1", "--format=%aI"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        timestamp = result.stdout.strip()
        return timestamp if timestamp else None

    def add_all(self, cwd: Path) -> None:
        """Stage all changes for commit (git add -A)."""
        run_subprocess_with_context(
            cmd=["git", "add", "-A"],
            operation_context="stage all changes",
            cwd=cwd,
        )

    def amend_commit(self, cwd: Path, message: str) -> None:
        """Amend the current commit with a new message."""
        run_subprocess_with_context(
            cmd=["git", "commit", "--amend", "-m", message],
            operation_context="amend commit",
            cwd=cwd,
        )

    def count_commits_ahead(self, cwd: Path, base_branch: str) -> int:
        """Count commits in HEAD that are not in base_branch."""
        result = subprocess.run(
            ["git", "rev-list", "--count", f"{base_branch}..HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return 0
        count_str = result.stdout.strip()
        if not count_str:
            return 0
        return int(count_str)

    def get_repository_root(self, cwd: Path) -> Path:
        """Get the repository root directory."""
        result = run_subprocess_with_context(
            cmd=["git", "rev-parse", "--show-toplevel"],
            operation_context="get repository root",
            cwd=cwd,
        )
        return Path(result.stdout.strip())

    def get_diff_to_branch(self, cwd: Path, branch: str) -> str:
        """Get diff between branch and HEAD."""
        result = run_subprocess_with_context(
            cmd=["git", "diff", f"{branch}...HEAD"],
            operation_context=f"get diff to branch '{branch}'",
            cwd=cwd,
        )
        return result.stdout

    def check_merge_conflicts(self, cwd: Path, base_branch: str, head_branch: str) -> bool:
        """Check if merging would have conflicts using git merge-tree."""
        result = subprocess.run(
            ["git", "merge-tree", "--write-tree", base_branch, head_branch],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode != 0

    def get_remote_url(self, repo_root: Path, remote: str = "origin") -> str:
        """Get the URL for a git remote.

        Raises:
            ValueError: If remote doesn't exist or has no URL
        """
        result = subprocess.run(
            ["git", "remote", "get-url", remote],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise ValueError(f"Remote '{remote}' not found in repository")
        url = result.stdout.strip()
        if not url:
            raise ValueError(f"Remote '{remote}' has no URL configured")
        return url

    def get_conflicted_files(self, cwd: Path) -> list[str]:
        """Parse git status --porcelain for UU/AA/DD/AU/UA/DU/UD status codes."""
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []

        conflict_codes = {"UU", "AA", "DD", "AU", "UA", "DU", "UD"}
        conflicted = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            status = line[:2]
            if status in conflict_codes:
                # File path starts at position 3
                conflicted.append(line[3:])
        return conflicted

    def is_rebase_in_progress(self, cwd: Path) -> bool:
        """Check for .git/rebase-merge or .git/rebase-apply directories."""
        git_common_dir = self.get_git_common_dir(cwd)
        if git_common_dir is None:
            return False
        rebase_merge = git_common_dir / "rebase-merge"
        rebase_apply = git_common_dir / "rebase-apply"
        return rebase_merge.exists() or rebase_apply.exists()

    def rebase_continue(self, cwd: Path) -> None:
        """Run git rebase --continue."""
        subprocess.run(
            ["git", "rebase", "--continue"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "GIT_EDITOR": "true"},  # Auto-accept commit messages
        )

    def get_commit_messages_since(self, cwd: Path, base_branch: str) -> list[str]:
        """Get full commit messages for commits in HEAD but not in base_branch."""
        separator = "---COMMIT_SEP---"
        result = subprocess.run(
            ["git", "log", "--reverse", f"--format=%B{separator}", f"{base_branch}..HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []
        return [msg.strip() for msg in result.stdout.split(separator) if msg.strip()]

    def config_set(self, cwd: Path, key: str, value: str, *, scope: str = "local") -> None:
        """Set a git configuration value."""
        run_subprocess_with_context(
            cmd=["git", "config", f"--{scope}", key, value],
            operation_context=f"set git config {key}",
            cwd=cwd,
        )

    def get_head_commit_message_full(self, cwd: Path) -> str:
        """Get the full commit message of HEAD."""
        result = subprocess.run(
            ["git", "log", "-1", "--format=%B", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def get_git_user_name(self, cwd: Path) -> str | None:
        """Get the configured git user.name."""
        result = subprocess.run(
            ["git", "config", "user.name"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        name = result.stdout.strip()
        return name if name else None

    def get_branch_commits_with_authors(
        self, repo_root: Path, branch: str, trunk: str, *, limit: int = 50
    ) -> list[dict[str, str]]:
        """Get commits on branch not on trunk, with author and timestamp."""
        result = subprocess.run(
            [
                "git",
                "log",
                f"{trunk}..{branch}",
                f"-n{limit}",
                "--format=%H%x00%an%x00%aI",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\x00")
            if len(parts) == 3:
                commits.append(
                    {
                        "sha": parts[0],
                        "author": parts[1],
                        "timestamp": parts[2],
                    }
                )
        return commits

    def tag_exists(self, repo_root: Path, tag_name: str) -> bool:
        """Check if a git tag exists."""
        result = subprocess.run(
            ["git", "tag", "-l", tag_name],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        return tag_name in result.stdout.strip().split("\n")

    def create_tag(self, repo_root: Path, tag_name: str, message: str) -> None:
        """Create an annotated git tag."""
        run_subprocess_with_context(
            cmd=["git", "tag", "-a", tag_name, "-m", message],
            operation_context=f"create tag '{tag_name}'",
            cwd=repo_root,
        )

    def push_tag(self, repo_root: Path, remote: str, tag_name: str) -> None:
        """Push a tag to a remote."""
        run_subprocess_with_context(
            cmd=["git", "push", remote, tag_name],
            operation_context=f"push tag '{tag_name}' to remote '{remote}'",
            cwd=repo_root,
        )

    def is_branch_diverged_from_remote(
        self, cwd: Path, branch: str, remote: str
    ) -> BranchDivergence:
        """Check if a local branch has diverged from its remote tracking branch."""
        remote_branch = f"{remote}/{branch}"

        # Check if remote branch exists
        result = subprocess.run(
            ["git", "rev-parse", "--verify", remote_branch],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return BranchDivergence(is_diverged=False, ahead=0, behind=0)

        # Get ahead/behind counts
        ahead_result = subprocess.run(
            ["git", "rev-list", "--count", f"{remote_branch}..{branch}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        behind_result = subprocess.run(
            ["git", "rev-list", "--count", f"{branch}..{remote_branch}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )

        ahead = int(ahead_result.stdout.strip()) if ahead_result.returncode == 0 else 0
        behind = int(behind_result.stdout.strip()) if behind_result.returncode == 0 else 0

        is_diverged = ahead > 0 and behind > 0
        return BranchDivergence(is_diverged=is_diverged, ahead=ahead, behind=behind)

    def rebase_onto(self, cwd: Path, target_ref: str) -> RebaseResult:
        """Rebase the current branch onto a target ref."""
        result = subprocess.run(
            ["git", "rebase", target_ref],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "GIT_EDITOR": "true"},  # Auto-accept commit messages
        )

        if result.returncode == 0:
            return RebaseResult(success=True, conflict_files=())

        # Rebase failed - get conflict files
        conflict_files = self.get_conflicted_files(cwd)
        return RebaseResult(success=False, conflict_files=tuple(conflict_files))

    def rebase_abort(self, cwd: Path) -> None:
        """Abort an in-progress rebase operation."""
        run_subprocess_with_context(
            cmd=["git", "rebase", "--abort"],
            operation_context="abort rebase",
            cwd=cwd,
        )

    def pull_rebase(self, cwd: Path, remote: str, branch: str) -> None:
        """Pull and rebase from remote branch."""
        run_subprocess_with_context(
            cmd=["git", "pull", "--rebase", remote, branch],
            operation_context=f"pull --rebase {remote} {branch}",
            cwd=cwd,
        )
