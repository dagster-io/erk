"""In-memory fake implementations of GT kit operations for testing.

This module provides fake implementations with declarative setup methods that
eliminate the need for extensive subprocess mocking in tests.

Design:
- Immutable state using frozen dataclasses
- Declarative setup methods (with_branch, with_uncommitted_files, etc.)
- Automatic state transitions (commit clears uncommitted files)
- LBYL pattern: methods check state before operations
- Returns match interface contracts exactly
"""

from dataclasses import dataclass, field, replace
from pathlib import Path

from erk_shared.git.abc import Git
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.types import BranchMetadata
from erk_shared.integrations.gt import (
    GitHubGtKit,
    GtKit,
)


@dataclass(frozen=True)
class GitState:
    """Immutable git repository state."""

    current_branch: str = "main"
    uncommitted_files: list[str] = field(default_factory=list)
    commits: list[str] = field(default_factory=list)
    branch_parents: dict[str, str] = field(default_factory=dict)
    add_success: bool = True
    trunk_branch: str = "main"
    tracked_files: list[str] = field(default_factory=list)
    repo_root: str = "/fake/repo/root"


@dataclass(frozen=True)
class GitHubState:
    """Immutable GitHub PR state."""

    pr_numbers: dict[str, int] = field(default_factory=dict)
    pr_urls: dict[str, str] = field(default_factory=dict)
    pr_states: dict[str, str] = field(default_factory=dict)
    pr_titles: dict[int, str] = field(default_factory=dict)
    pr_bodies: dict[int, str] = field(default_factory=dict)
    pr_diffs: dict[int, str] = field(default_factory=dict)
    pr_mergeability: dict[int, tuple[str, str]] = field(default_factory=dict)
    merge_success: bool = True
    pr_update_success: bool = True
    pr_delay_attempts_until_visible: int = 0
    authenticated: bool = True
    auth_username: str | None = "test-user"
    auth_hostname: str | None = "github.com"


class FakeGitGtKitOps(Git):
    """Fake git operations with in-memory state.

    This fake implements the Git interface and provides additional methods
    for backward compatibility with GitGtKit tests.
    """

    def __init__(self, state: GitState | None = None) -> None:
        """Initialize with optional initial state."""
        self._state = state if state is not None else GitState()

    def get_state(self) -> GitState:
        """Get current state (for testing assertions)."""
        return self._state

    def get_current_branch(self, cwd: Path) -> str | None:
        """Get the name of the current branch."""
        if not self._state.current_branch:
            return None
        return self._state.current_branch

    def has_uncommitted_changes(self, cwd: Path) -> bool:
        """Check if there are uncommitted changes."""
        return len(self._state.uncommitted_files) > 0

    def add_all(self, cwd: Path) -> None:
        """Stage all changes for commit."""
        import subprocess

        if not self._state.add_success:
            raise subprocess.CalledProcessError(1, ["git", "add", "-A"])

        # Track staged files separately for proper simulation
        # In a real git workflow, add_all stages files but doesn't commit them
        # For our fake, we'll track this via a staged_files field
        if not hasattr(self, "_staged_files"):
            self._staged_files: list[str] = []
        self._staged_files = list(self._state.uncommitted_files)

    def commit(self, cwd: Path, message: str) -> None:
        """Create a commit and clear uncommitted files."""
        # Create new state with commit added and uncommitted files cleared
        new_commits = [*self._state.commits, message]
        # Track committed files in the state
        tracked_files = getattr(self._state, "tracked_files", [])
        new_tracked = list(set(tracked_files + self._state.uncommitted_files))
        self._state = replace(
            self._state, commits=new_commits, uncommitted_files=[], tracked_files=new_tracked
        )
        # Clear staged files after commit
        if hasattr(self, "_staged_files"):
            self._staged_files = []

    def amend_commit(self, cwd: Path, message: str) -> None:
        """Amend the current commit message and include any staged changes."""
        import subprocess

        if not self._state.commits:
            raise subprocess.CalledProcessError(1, ["git", "commit", "--amend"])

        # Replace last commit message
        new_commits = [*self._state.commits[:-1], message]
        # Amend should include staged files and clear uncommitted files
        # (since they're now part of the amended commit)
        tracked_files = getattr(self._state, "tracked_files", [])
        new_tracked = list(set(tracked_files + self._state.uncommitted_files))
        self._state = replace(
            self._state, commits=new_commits, uncommitted_files=[], tracked_files=new_tracked
        )
        # Clear staged files after amend
        if hasattr(self, "_staged_files"):
            self._staged_files = []

    def count_commits_in_branch(self, parent_branch: str) -> int:
        """Count commits in current branch.

        For fakes, this returns the total number of commits since we don't
        track per-branch commit history in detail.
        """
        return len(self._state.commits)

    def count_commits_ahead(self, cwd: Path, base_branch: str) -> int:
        """Count commits in HEAD that are not in base_branch."""
        return len(self._state.commits)

    def get_trunk_branch(self, repo_root: Path) -> str:
        """Get the trunk branch name for the repository."""
        return self._state.trunk_branch

    def get_repository_root(self, cwd: Path) -> Path:
        """Fake repository root."""
        return Path(self._state.repo_root)

    def get_diff_to_parent(self, parent_branch: str) -> str:
        """Fake diff output."""
        return (
            "diff --git a/file.py b/file.py\n"
            "--- a/file.py\n"
            "+++ b/file.py\n"
            "@@ -1,1 +1,1 @@\n"
            "-old\n"
            "+new"
        )

    def check_merge_conflicts(self, cwd: Path, base_branch: str, head_branch: str) -> bool:
        """Fake conflict checker - returns False unless configured otherwise."""
        # Check if fake has been configured to simulate conflicts
        if hasattr(self, "_simulated_conflicts"):
            return (base_branch, head_branch) in self._simulated_conflicts
        return False

    def get_diff_to_branch(self, cwd: Path, branch: str) -> str:
        """Get diff between branch and HEAD."""
        return (
            "diff --git a/file.py b/file.py\n"
            "--- a/file.py\n"
            "+++ b/file.py\n"
            "@@ -1,1 +1,1 @@\n"
            "-old\n"
            "+new"
        )

    def simulate_conflict(self, base_branch: str, head_branch: str) -> None:
        """Configure fake to simulate conflicts for specific branch pair."""
        if not hasattr(self, "_simulated_conflicts"):
            self._simulated_conflicts: set[tuple[str, str]] = set()
        self._simulated_conflicts.add((base_branch, head_branch))

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Fake git common directory - returns a path based on repo_root."""
        return Path(self._state.repo_root) / ".git"

    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        """Fake branch head - returns a static SHA for testing."""
        # Return a fake SHA based on branch name for deterministic testing
        return f"fake-sha-for-{branch}"

    def checkout_branch(self, cwd: Path, branch: str) -> None:
        """Fake branch checkout - updates current branch state."""
        self._state = replace(self._state, current_branch=branch)

    # Stub implementations for unused Git ABC methods
    def list_worktrees(self, repo_root: Path) -> list:
        """Stub."""
        raise NotImplementedError

    def detect_default_branch(self, repo_root: Path, configured: str | None = None) -> str:
        """Stub."""
        raise NotImplementedError

    def list_local_branches(self, repo_root: Path) -> list[str]:
        """Stub."""
        raise NotImplementedError

    def list_remote_branches(self, repo_root: Path) -> list[str]:
        """Stub."""
        raise NotImplementedError

    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        """Stub."""
        raise NotImplementedError

    def has_staged_changes(self, repo_root: Path) -> bool:
        """Stub."""
        raise NotImplementedError

    def is_worktree_clean(self, worktree_path: Path) -> bool:
        """Stub."""
        raise NotImplementedError

    def add_worktree(
        self,
        repo_root: Path,
        path: Path,
        *,
        branch: str | None = None,
        ref: str | None = None,
        create_branch: bool = False,
    ) -> None:
        """Stub."""
        raise NotImplementedError

    def move_worktree(self, repo_root: Path, old_path: Path, new_path: Path) -> None:
        """Stub."""
        raise NotImplementedError

    def remove_worktree(self, repo_root: Path, path: Path, *, force: bool) -> None:
        """Stub."""
        raise NotImplementedError

    def checkout_detached(self, cwd: Path, ref: str) -> None:
        """Stub."""
        raise NotImplementedError

    def create_branch(self, cwd: Path, branch_name: str, start_point: str) -> None:
        """Stub."""
        raise NotImplementedError

    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        """Stub."""
        raise NotImplementedError

    def delete_branch_with_graphite(self, repo_root: Path, branch: str, *, force: bool) -> None:
        """Stub."""
        raise NotImplementedError

    def prune_worktrees(self, repo_root: Path) -> None:
        """Stub."""
        raise NotImplementedError

    def path_exists(self, path: Path) -> bool:
        """Stub."""
        raise NotImplementedError

    def is_dir(self, path: Path) -> bool:
        """Stub."""
        raise NotImplementedError

    def safe_chdir(self, path: Path) -> bool:
        """Stub."""
        raise NotImplementedError

    def is_branch_checked_out(self, repo_root: Path, branch: str) -> Path | None:
        """Stub."""
        raise NotImplementedError

    def find_worktree_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        """Stub."""
        raise NotImplementedError

    def get_commit_message(self, repo_root: Path, commit_sha: str) -> str | None:
        """Stub."""
        raise NotImplementedError

    def get_file_status(self, cwd: Path) -> tuple[list[str], list[str], list[str]]:
        """Stub."""
        raise NotImplementedError

    def get_ahead_behind(self, cwd: Path, branch: str) -> tuple[int, int]:
        """Stub."""
        raise NotImplementedError

    def get_all_branch_sync_info(self, repo_root: Path) -> dict:
        """Stub."""
        raise NotImplementedError

    def get_recent_commits(self, cwd: Path, *, limit: int = 5) -> list[dict[str, str]]:
        """Stub."""
        raise NotImplementedError

    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        """Stub."""
        raise NotImplementedError

    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        """Stub."""
        raise NotImplementedError

    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        """Stub."""
        raise NotImplementedError

    def set_branch_issue(self, repo_root: Path, branch: str, issue_number: int) -> None:
        """Stub."""
        raise NotImplementedError

    def get_branch_issue(self, repo_root: Path, branch: str) -> int | None:
        """Stub."""
        raise NotImplementedError

    def fetch_pr_ref(self, repo_root: Path, remote: str, pr_number: int, local_branch: str) -> None:
        """Stub."""
        raise NotImplementedError

    def stage_files(self, cwd: Path, paths: list[str]) -> None:
        """Stub."""
        raise NotImplementedError

    def push_to_remote(
        self, cwd: Path, remote: str, branch: str, *, set_upstream: bool = False
    ) -> None:
        """Stub."""
        raise NotImplementedError

    def get_branch_last_commit_time(self, repo_root: Path, branch: str, trunk: str) -> str | None:
        """Stub."""
        return None

    def read_file(self, path: Path) -> str:
        """Stub."""
        raise NotImplementedError


class FakeGitHubGtKitOps(GitHubGtKit):
    """Fake GitHub operations with in-memory state."""

    def __init__(self, state: GitHubState | None = None) -> None:
        """Initialize with optional initial state."""
        self._state = state if state is not None else GitHubState()
        self._current_branch = "main"
        self._pr_info_attempt_count = 0

    def set_current_branch(self, branch: str) -> None:
        """Set current branch (needed for context)."""
        self._current_branch = branch

    def get_state(self) -> GitHubState:
        """Get current state (for testing assertions)."""
        return self._state

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Return pre-configured authentication status."""
        if not self._state.authenticated:
            return (False, None, None)
        return (True, self._state.auth_username, self._state.auth_hostname)

    def get_pr_info(self) -> tuple[int, str] | None:
        """Get PR number and URL for current branch."""
        # Simulate PR delay if configured
        if self._state.pr_delay_attempts_until_visible > 0:
            self._pr_info_attempt_count += 1
            if self._pr_info_attempt_count <= self._state.pr_delay_attempts_until_visible:
                return None

        if self._current_branch not in self._state.pr_numbers:
            return None

        pr_number = self._state.pr_numbers[self._current_branch]
        pr_url = self._state.pr_urls.get(
            self._current_branch, f"https://github.com/repo/pull/{pr_number}"
        )
        return (pr_number, pr_url)

    def get_pr_state(self) -> tuple[int, str] | None:
        """Get PR number and state for current branch."""
        if self._current_branch not in self._state.pr_numbers:
            return None

        pr_number = self._state.pr_numbers[self._current_branch]
        pr_state = self._state.pr_states.get(self._current_branch, "OPEN")
        return (pr_number, pr_state)

    def update_pr_metadata(self, title: str, body: str) -> bool:
        """Update PR title and body with configurable success/failure."""
        if self._current_branch not in self._state.pr_numbers:
            return False

        if not self._state.pr_update_success:
            return False

        pr_number = self._state.pr_numbers[self._current_branch]

        # Create new state with updated metadata
        new_titles = {**self._state.pr_titles, pr_number: title}
        new_bodies = {**self._state.pr_bodies, pr_number: body}
        self._state = replace(self._state, pr_titles=new_titles, pr_bodies=new_bodies)
        return True

    def mark_pr_ready(self) -> bool:
        """Mark PR as ready for review (fake always succeeds if PR exists)."""
        if self._current_branch not in self._state.pr_numbers:
            return False
        # In the fake, marking as ready always succeeds if PR exists
        return True

    def get_pr_title(self) -> str | None:
        """Get the title of the PR for the current branch."""
        if self._current_branch not in self._state.pr_numbers:
            return None
        pr_number = self._state.pr_numbers[self._current_branch]
        return self._state.pr_titles.get(pr_number)

    def get_pr_body(self) -> str | None:
        """Get the body of the PR for the current branch."""
        if self._current_branch not in self._state.pr_numbers:
            return None
        pr_number = self._state.pr_numbers[self._current_branch]
        return self._state.pr_bodies.get(pr_number)

    def merge_pr(self, *, subject: str | None = None, body: str | None = None) -> bool:
        """Merge the PR with configurable success/failure."""
        if self._current_branch not in self._state.pr_numbers:
            return False
        return self._state.merge_success

    def get_graphite_pr_url(self, pr_number: int) -> str | None:
        """Get Graphite PR URL (fake returns test URL)."""
        return f"https://app.graphite.com/github/pr/test-owner/test-repo/{pr_number}"

    def get_pr_diff(self, pr_number: int) -> str:
        """Get PR diff from configured state or return default."""
        if pr_number in self._state.pr_diffs:
            return self._state.pr_diffs[pr_number]
        # Return a simple default diff
        return (
            "diff --git a/file.py b/file.py\n"
            "--- a/file.py\n"
            "+++ b/file.py\n"
            "@@ -1,1 +1,1 @@\n"
            "-old\n"
            "+new"
        )

    def get_pr_status(self, branch: str) -> tuple[int | None, str | None]:
        """Get PR number and URL for branch from fake state."""
        if branch not in self._state.pr_numbers:
            return (None, None)

        pr_number = self._state.pr_numbers[branch]
        pr_url = self._state.pr_urls.get(branch, f"https://github.com/repo/pull/{pr_number}")
        return (pr_number, pr_url)

    def get_pr_mergeability(self, pr_number: int) -> tuple[str, str]:
        """Get PR mergeability status from fake state."""
        # Default: MERGEABLE/CLEAN unless configured otherwise
        return self._state.pr_mergeability.get(pr_number, ("MERGEABLE", "CLEAN"))


class FakeGtKitOps(GtKit):
    """Fake composite operations for testing.

    Provides declarative setup methods for common test scenarios.
    """

    def __init__(
        self,
        git_state: GitState | None = None,
        github_state: GitHubState | None = None,
        main_graphite: Graphite | None = None,
    ) -> None:
        """Initialize with optional initial states."""
        self._git = FakeGitGtKitOps(git_state)
        self._github = FakeGitHubGtKitOps(github_state)
        self._main_graphite = main_graphite if main_graphite is not None else FakeGraphite()

    def git(self) -> Git:
        """Get the git operations interface."""
        return self._git  # type: ignore[return-value]

    def github(self) -> FakeGitHubGtKitOps:
        """Get the GitHub operations interface."""
        return self._github

    def main_graphite(self) -> Graphite:
        """Get the main Graphite operations interface."""
        return self._main_graphite

    # Declarative setup methods

    def with_branch(self, branch: str, parent: str = "main") -> "FakeGtKitOps":
        """Set current branch and its parent.

        Args:
            branch: Branch name
            parent: Parent branch name

        Returns:
            Self for chaining
        """
        # Update git state
        git_state = self._git.get_state()
        self._git._state = replace(git_state, current_branch=branch)

        # Update github state
        self._github.set_current_branch(branch)

        # Configure main_graphite fake to track the parent relationship
        if hasattr(self._main_graphite, "track_branch"):
            repo_root = Path(self._git.get_state().repo_root)
            self._main_graphite.track_branch(repo_root, branch, parent)

        return self

    def with_uncommitted_files(self, files: list[str]) -> "FakeGtKitOps":
        """Set uncommitted files.

        Args:
            files: List of file paths

        Returns:
            Self for chaining
        """
        git_state = self._git.get_state()
        self._git._state = replace(git_state, uncommitted_files=files)
        return self

    def with_repo_root(self, repo_root: str) -> "FakeGtKitOps":
        """Set the repository root path.

        Args:
            repo_root: Path to repository root

        Returns:
            Self for chaining
        """
        git_state = self._git.get_state()
        self._git._state = replace(git_state, repo_root=repo_root)
        return self

    def with_commits(self, count: int) -> "FakeGtKitOps":
        """Add a number of commits.

        Args:
            count: Number of commits to add

        Returns:
            Self for chaining
        """
        git_state = self._git.get_state()
        commits = [f"commit-{i}" for i in range(count)]
        self._git._state = replace(git_state, commits=commits)
        return self

    def with_pr(
        self,
        number: int,
        *,
        url: str | None = None,
        state: str = "OPEN",
        title: str | None = None,
        body: str | None = None,
    ) -> "FakeGtKitOps":
        """Set PR for current branch.

        Args:
            number: PR number
            url: PR URL (auto-generated if None)
            state: PR state (default: OPEN)
            title: PR title (optional)
            body: PR body (optional)

        Returns:
            Self for chaining
        """
        gh_state = self._github.get_state()
        branch = self._github._current_branch

        if url is None:
            url = f"https://github.com/repo/pull/{number}"

        new_pr_numbers = {**gh_state.pr_numbers, branch: number}
        new_pr_urls = {**gh_state.pr_urls, branch: url}
        new_pr_states = {**gh_state.pr_states, branch: state}
        new_pr_titles = gh_state.pr_titles
        new_pr_bodies = gh_state.pr_bodies
        if title is not None:
            new_pr_titles = {**gh_state.pr_titles, number: title}
        if body is not None:
            new_pr_bodies = {**gh_state.pr_bodies, number: body}

        self._github._state = replace(
            gh_state,
            pr_numbers=new_pr_numbers,
            pr_urls=new_pr_urls,
            pr_states=new_pr_states,
            pr_titles=new_pr_titles,
            pr_bodies=new_pr_bodies,
        )
        return self

    def with_children(self, children: list[str]) -> "FakeGtKitOps":
        """Set child branches for current branch.

        Args:
            children: List of child branch names

        Returns:
            Self for chaining
        """
        # Track children relationships in main_graphite for each child
        if hasattr(self._main_graphite, "track_branch"):
            current_branch = self._git.get_state().current_branch
            repo_root = Path(self._git.get_state().repo_root)
            for child in children:
                self._main_graphite.track_branch(repo_root, child, current_branch)

        return self

    def with_submit_failure(self, stderr: str = "") -> "FakeGtKitOps":
        """Configure submit_stack to fail via main_graphite.

        Args:
            stderr: Error message to include

        Returns:
            Self for chaining
        """
        # Configure main_graphite to raise RuntimeError for submit_stack
        existing_branches: dict[str, BranchMetadata] = {}
        if isinstance(self._main_graphite, FakeGraphite):
            existing_branches = self._main_graphite._branches
        error = RuntimeError(f"gt submit failed: {stderr}")
        self._main_graphite = FakeGraphite(
            submit_stack_raises=error,
            branches=existing_branches,
        )
        return self

    def with_restack_failure(self, stdout: str = "", stderr: str = "") -> "FakeGtKitOps":
        """Configure restack to fail.

        Args:
            stdout: Stdout to return
            stderr: Stderr to return

        Returns:
            Self for chaining
        """
        import subprocess

        # Configure main_graphite to raise CalledProcessError for restack
        error = subprocess.CalledProcessError(returncode=1, cmd=["gt", "restack"])
        error.stdout = stdout
        error.stderr = stderr
        existing_branches: dict[str, BranchMetadata] = {}
        if isinstance(self._main_graphite, FakeGraphite):
            existing_branches = self._main_graphite._branches
        self._main_graphite = FakeGraphite(
            restack_raises=error,
            branches=existing_branches,
        )
        return self

    def with_merge_failure(self) -> "FakeGtKitOps":
        """Configure PR merge to fail.

        Returns:
            Self for chaining
        """
        gh_state = self._github.get_state()
        self._github._state = replace(gh_state, merge_success=False)
        return self

    def with_squash_failure(self, stdout: str = "", stderr: str = "") -> "FakeGtKitOps":
        """Configure squash_branch to fail via main_graphite.

        Args:
            stdout: Stdout to include
            stderr: Error message to include

        Returns:
            Self for chaining
        """
        import subprocess

        # Configure main_graphite to raise CalledProcessError for squash
        error = subprocess.CalledProcessError(returncode=1, cmd=["gt", "squash"])
        error.stdout = stdout
        error.stderr = stderr
        existing_branches: dict[str, BranchMetadata] = {}
        if isinstance(self._main_graphite, FakeGraphite):
            existing_branches = self._main_graphite._branches
        self._main_graphite = FakeGraphite(
            squash_branch_raises=error,
            branches=existing_branches,
        )
        return self

    def with_add_failure(self) -> "FakeGtKitOps":
        """Configure git add to fail.

        Returns:
            Self for chaining
        """
        git_state = self._git.get_state()
        self._git._state = replace(git_state, add_success=False)
        return self

    def with_pr_update_failure(self) -> "FakeGtKitOps":
        """Configure PR metadata update to fail.

        Returns:
            Self for chaining
        """
        gh_state = self._github.get_state()
        self._github._state = replace(gh_state, pr_update_success=False)
        return self

    def with_pr_delay(self, attempts_until_visible: int) -> "FakeGtKitOps":
        """Configure PR to appear only after N get_pr_info() attempts.

        Simulates GitHub API delay where PR is not immediately visible after creation.

        Args:
            attempts_until_visible: Number of attempts that return None before PR appears

        Returns:
            Self for chaining
        """
        gh_state = self._github.get_state()
        self._github._state = replace(
            gh_state, pr_delay_attempts_until_visible=attempts_until_visible
        )
        return self

    def with_submit_success_but_nothing_submitted(self) -> "FakeGtKitOps":
        """Configure submit_stack to fail with 'Nothing to submit!' error.

        Simulates the case where a parent branch is empty/already merged.

        Returns:
            Self for chaining
        """
        # Configure main_graphite to raise RuntimeError with nothing submitted message
        existing_branches: dict[str, BranchMetadata] = {}
        if isinstance(self._main_graphite, FakeGraphite):
            existing_branches = self._main_graphite._branches
        error = RuntimeError(
            "gt submit failed: WARNING: This branch does not introduce any changes:\n"
            "▸ stale-parent-branch\n"
            "WARNING: This branch and any dependent branches will not be submitted.\n"
            "Nothing to submit!"
        )
        self._main_graphite = FakeGraphite(
            submit_stack_raises=error,
            branches=existing_branches,
        )
        return self

    def with_gt_unauthenticated(self) -> "FakeGtKitOps":
        """Configure Graphite as not authenticated.

        Returns:
            Self for chaining
        """
        # Configure main_graphite to return unauthenticated status
        existing_branches: dict[str, BranchMetadata] = {}
        if isinstance(self._main_graphite, FakeGraphite):
            existing_branches = self._main_graphite._branches
        self._main_graphite = FakeGraphite(
            authenticated=False,
            auth_username=None,
            auth_repo_info=None,
            branches=existing_branches,
        )
        return self

    def with_gh_unauthenticated(self) -> "FakeGtKitOps":
        """Configure GitHub as not authenticated.

        Returns:
            Self for chaining
        """
        gh_state = self._github.get_state()
        self._github._state = replace(
            gh_state,
            authenticated=False,
            auth_username=None,
            auth_hostname=None,
        )
        return self

    def with_pr_conflicts(self, pr_number: int) -> "FakeGtKitOps":
        """Configure PR to have merge conflicts.

        Args:
            pr_number: PR number to configure as conflicting

        Returns:
            Self for chaining
        """
        gh_state = self._github.get_state()
        new_mergeability = {
            **gh_state.pr_mergeability,
            pr_number: ("CONFLICTING", "DIRTY"),
        }
        self._github._state = replace(gh_state, pr_mergeability=new_mergeability)
        return self

    def with_pr_mergeability(
        self, pr_number: int, mergeable: str, merge_state: str
    ) -> "FakeGtKitOps":
        """Configure PR mergeability status.

        Args:
            pr_number: PR number to configure
            mergeable: Mergeability status ("MERGEABLE", "CONFLICTING", "UNKNOWN")
            merge_state: Merge state status ("CLEAN", "DIRTY", "UNSTABLE", etc.)

        Returns:
            Self for chaining
        """
        gh_state = self._github.get_state()
        new_mergeability = {
            **gh_state.pr_mergeability,
            pr_number: (mergeable, merge_state),
        }
        self._github._state = replace(gh_state, pr_mergeability=new_mergeability)
        return self

    def with_restack_conflict(self) -> "FakeGtKitOps":
        """Configure restack to fail with conflicts.

        Returns:
            Self for chaining
        """
        return self.with_restack_failure(
            stderr="error: merge conflict in file.py\nCONFLICT (content): Merge conflict in file.py"
        )

    def with_squash_conflict(self) -> "FakeGtKitOps":
        """Configure squash to fail with conflicts.

        Returns:
            Self for chaining
        """
        return self.with_squash_failure(
            stderr="error: merge conflict in file.py\nCONFLICT (content): Merge conflict in file.py"
        )
