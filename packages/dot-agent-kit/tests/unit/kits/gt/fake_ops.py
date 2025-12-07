"""In-memory fake implementations of GT kit operations for testing.

This module provides fake implementations with declarative setup methods that
eliminate the need for extensive subprocess mocking in tests.

Design:
- Immutable state using frozen dataclasses
- Declarative setup methods (with_branch, with_uncommitted_files, etc.)
- Automatic state transitions (commit clears uncommitted files)
- LBYL pattern: methods check state before operations
- Returns match interface contracts exactly
- Satisfies GtKit Protocol through structural typing
"""

from dataclasses import dataclass, field
from pathlib import Path

from erk_shared.git.abc import Git
from erk_shared.git.fake import FakeGit
from erk_shared.github.abc import GitHub
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.types import BranchMetadata


@dataclass
class GitBuilderState:
    """Mutable builder state for constructing FakeGit instances."""

    conflicted_files: list[str] = field(default_factory=list)
    rebase_in_progress: bool = False
    rebase_continue_raises: Exception | None = None
    existing_paths: set[Path] = field(default_factory=set)
    dirty_worktrees: set[Path] = field(default_factory=set)


@dataclass
class GitHubBuilderState:
    """Mutable builder state for constructing FakeGitHub instances.

    This dataclass accumulates configuration from builder methods
    and is used to construct a FakeGitHub instance on demand.
    """

    pr_numbers: dict[str, int] = field(default_factory=dict)
    pr_urls: dict[str, str] = field(default_factory=dict)
    pr_states: dict[str, str] = field(default_factory=dict)
    pr_titles: dict[int, str] = field(default_factory=dict)
    pr_bodies: dict[int, str] = field(default_factory=dict)
    pr_diffs: dict[int, str] = field(default_factory=dict)
    pr_mergeability: dict[int, tuple[str, str]] = field(default_factory=dict)
    merge_should_succeed: bool = True
    pr_update_should_succeed: bool = True
    authenticated: bool = True
    auth_username: str | None = "test-user"
    auth_hostname: str | None = "github.com"
    current_branch: str = "main"


class FakeGtKitOps:
    """Fake composite operations for testing.

    Provides declarative setup methods for common test scenarios.
    Satisfies the GtKit Protocol through structural typing.
    Uses lazy construction to build FakeGitHub from accumulated builder state.
    """

    def __init__(
        self,
        github_builder_state: GitHubBuilderState | None = None,
        git_builder_state: GitBuilderState | None = None,
        main_graphite: Graphite | None = None,
    ) -> None:
        """Initialize with optional initial states."""
        # State accumulators for FakeGit (lazy construction)
        self._git_current_branches: dict[Path, str | None] = {}
        self._git_trunk_branches: dict[Path, str] = {}
        self._git_parent_branches: dict[Path, str] = {}  # Parent branch per repo (for Graphite)
        self._git_repository_roots: dict[Path, Path] = {}
        self._git_file_statuses: dict[Path, tuple[list[str], list[str], list[str]]] = {}
        self._git_commits_ahead: dict[tuple[Path, str], int] = {}
        self._git_diff_to_branch: dict[tuple[Path, str], str] = {}
        self._git_merge_conflicts: dict[tuple[str, str], bool] = {}
        self._git_add_all_raises: Exception | None = None
        self._git_remote_urls: dict[tuple[Path, str], str] = {}
        self._git_instance: FakeGit | None = None
        self._repo_root: str = "/fake/repo/root"

        # Git builder state for restack-related tests
        self._git_builder_state = (
            git_builder_state if git_builder_state is not None else GitBuilderState()
        )

        # GitHub builder state (lazy construction)
        self._github_builder_state = (
            github_builder_state if github_builder_state is not None else GitHubBuilderState()
        )
        self._github_instance: FakeGitHub | None = None

        # Graphite instance
        self._main_graphite = main_graphite if main_graphite is not None else FakeGraphite()

    def _build_fake_git(self) -> FakeGit:
        """Build FakeGit from accumulated state.

        For test compatibility, we duplicate state across all possible path variations
        so tests work regardless of which path is used to query state.
        """
        # Duplicate current_branches across path variations for test compatibility
        current_branches_expanded = dict(self._git_current_branches)
        trunk_branches_expanded = dict(self._git_trunk_branches)
        repository_roots_expanded = dict(self._git_repository_roots)
        file_statuses_expanded = dict(self._git_file_statuses)
        commits_ahead_expanded = dict(self._git_commits_ahead)

        # Add entries for Path.cwd() to handle tests that don't mock cwd
        if self._git_current_branches:
            # Copy state to current directory for compatibility
            from pathlib import Path

            cwd = Path.cwd()
            for repo_root, branch in self._git_current_branches.items():
                current_branches_expanded[cwd] = branch
                if repo_root in self._git_trunk_branches:
                    trunk_branches_expanded[cwd] = self._git_trunk_branches[repo_root]
                if repo_root in self._git_repository_roots:
                    repository_roots_expanded[cwd] = self._git_repository_roots[repo_root]
                if repo_root in self._git_file_statuses:
                    file_statuses_expanded[cwd] = self._git_file_statuses[repo_root]
                # Copy commits_ahead with cwd key
                for (path, base), count in self._git_commits_ahead.items():
                    if path == repo_root:
                        commits_ahead_expanded[(cwd, base)] = count

        # Provide default diff output for all repo roots
        diff_to_branch = dict(self._git_diff_to_branch)
        for repo_root in self._git_repository_roots:
            # Add default diff for trunk branch if not specified
            trunk = self._git_trunk_branches.get(repo_root, "main")
            default_diff = (
                "diff --git a/file.py b/file.py\n"
                "--- a/file.py\n"
                "+++ b/file.py\n"
                "@@ -1,1 +1,1 @@\n"
                "-old\n"
                "+new"
            )
            if (repo_root, trunk) not in diff_to_branch:
                diff_to_branch[(repo_root, trunk)] = default_diff
            # Also add cwd-based key for compatibility
            if self._git_current_branches:
                from pathlib import Path

                cwd = Path.cwd()
                if (cwd, trunk) not in diff_to_branch:
                    diff_to_branch[(cwd, trunk)] = default_diff

        return FakeGit(
            current_branches=current_branches_expanded,
            trunk_branches=trunk_branches_expanded,
            repository_roots=repository_roots_expanded,
            file_statuses=file_statuses_expanded,
            commits_ahead=commits_ahead_expanded,
            diff_to_branch=diff_to_branch,
            merge_conflicts=self._git_merge_conflicts,
            add_all_raises=self._git_add_all_raises,
            remote_urls=self._git_remote_urls,
            conflicted_files=self._git_builder_state.conflicted_files,
            rebase_in_progress=self._git_builder_state.rebase_in_progress,
            rebase_continue_raises=self._git_builder_state.rebase_continue_raises,
            existing_paths=self._git_builder_state.existing_paths or None,
            dirty_worktrees=self._git_builder_state.dirty_worktrees or None,
        )

    @property
    def git(self) -> Git:
        """Get the git operations interface (lazy construction)."""
        if self._git_instance is None:
            self._git_instance = self._build_fake_git()
        return self._git_instance

    @property
    def github(self) -> GitHub:
        """Get the GitHub operations interface.

        Constructs FakeGitHub lazily from accumulated builder state.
        """
        if self._github_instance is None:
            self._github_instance = self._build_fake_github()
        return self._github_instance

    def _build_fake_github(self) -> FakeGitHub:
        """Build FakeGitHub from accumulated builder state."""
        # Build prs dict from pr_numbers, pr_urls, pr_states
        prs: dict[str, PullRequestInfo] = {}
        for branch, pr_number in self._github_builder_state.pr_numbers.items():
            pr_url = self._github_builder_state.pr_urls.get(
                branch, f"https://github.com/repo/pull/{pr_number}"
            )
            pr_state = self._github_builder_state.pr_states.get(branch, "OPEN")
            pr_title = self._github_builder_state.pr_titles.get(pr_number)
            prs[branch] = PullRequestInfo(
                number=pr_number,
                state=pr_state,
                url=pr_url,
                is_draft=False,
                title=pr_title,
                checks_passing=None,
                owner="test-owner",
                repo="test-repo",
                has_conflicts=None,
            )

        # Build pr_details from accumulated state for get_pr() and get_pr_for_branch()
        pr_details: dict[int, PRDetails] = {}
        for branch, pr_number in self._github_builder_state.pr_numbers.items():
            pr_url = self._github_builder_state.pr_urls.get(
                branch, f"https://github.com/repo/pull/{pr_number}"
            )
            pr_state = self._github_builder_state.pr_states.get(branch, "OPEN")
            pr_title = self._github_builder_state.pr_titles.get(pr_number, "")
            pr_body = self._github_builder_state.pr_bodies.get(pr_number, "")

            # Get mergeability info or use defaults
            if pr_number in self._github_builder_state.pr_mergeability:
                mergeable, merge_state = self._github_builder_state.pr_mergeability[pr_number]
            else:
                mergeable, merge_state = "MERGEABLE", "CLEAN"

            # Get parent branch from graphite tracking if available
            base_ref = "master"  # Default base branch
            if isinstance(self._main_graphite, FakeGraphite):
                branch_info = self._main_graphite._branches.get(branch)
                if branch_info and branch_info.parent:
                    base_ref = branch_info.parent

            pr_details[pr_number] = PRDetails(
                number=pr_number,
                url=pr_url,
                title=pr_title or "",
                body=pr_body,
                state=pr_state,
                is_draft=False,
                base_ref_name=base_ref,
                head_ref_name=branch,
                is_cross_repository=False,
                mergeable=mergeable,
                merge_state_status=merge_state,
                owner="test-owner",
                repo="test-repo",
            )

        return FakeGitHub(
            prs=prs,
            pr_titles=self._github_builder_state.pr_titles,
            pr_bodies_by_number=self._github_builder_state.pr_bodies,
            pr_diffs=self._github_builder_state.pr_diffs,
            pr_details=pr_details,
            merge_should_succeed=self._github_builder_state.merge_should_succeed,
            pr_update_should_succeed=self._github_builder_state.pr_update_should_succeed,
            authenticated=self._github_builder_state.authenticated,
            auth_username=self._github_builder_state.auth_username,
            auth_hostname=self._github_builder_state.auth_hostname,
        )

    @property
    def graphite(self) -> Graphite:
        """Get the Graphite operations interface."""
        return self._main_graphite

    # Declarative setup methods

    def with_branch(self, branch: str, parent: str = "main") -> "FakeGtKitOps":
        """Set current branch and its parent.

        Args:
            branch: Branch name
            parent: Parent branch name (for Graphite tracking, not trunk)

        Returns:
            Self for chaining

        Note:
            This only sets the parent for Graphite tracking. It does NOT set the
            trunk branch. Use with_trunk_branch() to override the default trunk
            (which is "main"). For example:
            - with_branch("feature", parent="main") - feature branch on main trunk
            - with_branch("feature", parent="develop") - feature branch on develop
              (not trunk, will fail land_pr validation if trunk is "main")
        """
        repo_root = Path(self._repo_root)
        self._git_current_branches[repo_root] = branch
        # Store parent branch for with_commits to use
        self._git_parent_branches[repo_root] = parent
        # Do NOT set trunk here - trunk defaults to "main" in FakeGit.detect_trunk_branch()
        # Use with_trunk_branch() to override if needed
        # Ensure repository_roots is also set (needed for get_repository_root)
        self._git_repository_roots[repo_root] = repo_root
        self._git_instance = None  # Reset cache

        # Update github builder state
        self._github_builder_state.current_branch = branch
        self._github_instance = None

        # Configure graphite parent tracking
        if hasattr(self._main_graphite, "track_branch"):
            self._main_graphite.track_branch(repo_root, branch, parent)

        return self

    def with_uncommitted_files(self, files: list[str]) -> "FakeGtKitOps":
        """Set uncommitted files.

        Args:
            files: List of file paths

        Returns:
            Self for chaining
        """
        repo_root = Path(self._repo_root)
        # FakeGit uses file_statuses: dict[Path, tuple[staged, modified, untracked]]
        self._git_file_statuses[repo_root] = ([], files, [])  # files as modified
        self._git_instance = None
        return self

    def with_repo_root(self, repo_root: str) -> "FakeGtKitOps":
        """Set the repository root path.

        Args:
            repo_root: Path to repository root

        Returns:
            Self for chaining
        """
        self._repo_root = repo_root
        path = Path(repo_root)
        self._git_repository_roots[path] = path
        self._git_instance = None
        return self

    def with_commits(self, count: int) -> "FakeGtKitOps":
        """Add a number of commits.

        Args:
            count: Number of commits to add

        Returns:
            Self for chaining

        Note:
            Uses the parent branch from with_branch() for commit counting.
            This matches how the code counts commits against the parent branch.
        """
        repo_root = Path(self._repo_root)
        # FakeGit uses commits_ahead: dict[(Path, base_branch), int]
        # Use parent branch if set, otherwise fall back to trunk or "main"
        parent = self._git_parent_branches.get(repo_root)
        if parent is None:
            parent = self._git_trunk_branches.get(repo_root, "main")
        self._git_commits_ahead[(repo_root, parent)] = count
        self._git_instance = None
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
        branch = self._github_builder_state.current_branch

        if url is None:
            url = f"https://github.com/repo/pull/{number}"

        self._github_builder_state.pr_numbers[branch] = number
        self._github_builder_state.pr_urls[branch] = url
        self._github_builder_state.pr_states[branch] = state
        if title is not None:
            self._github_builder_state.pr_titles[number] = title
        if body is not None:
            self._github_builder_state.pr_bodies[number] = body

        # Reset cached instance since state changed
        self._github_instance = None
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
            repo_root = Path(self._repo_root)
            current_branch = self._git_current_branches.get(repo_root) or "main"
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
        self._github_builder_state.merge_should_succeed = False
        # Reset cached instance since state changed
        self._github_instance = None
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
        import subprocess

        error = subprocess.CalledProcessError(returncode=1, cmd=["git", "add", "-A"])
        self._git_add_all_raises = error
        self._git_instance = None  # Reset cache
        return self

    def with_pr_update_failure(self) -> "FakeGtKitOps":
        """Configure PR metadata update to fail.

        Returns:
            Self for chaining
        """
        self._github_builder_state.pr_update_should_succeed = False
        # Reset cached instance since state changed
        self._github_instance = None
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
        self._github_builder_state.authenticated = False
        self._github_builder_state.auth_username = None
        self._github_builder_state.auth_hostname = None
        # Reset cached instance since state changed
        self._github_instance = None
        return self

    def with_pr_conflicts(self, pr_number: int) -> "FakeGtKitOps":
        """Configure PR to have merge conflicts.

        Args:
            pr_number: PR number to configure as conflicting

        Returns:
            Self for chaining
        """
        self._github_builder_state.pr_mergeability[pr_number] = ("CONFLICTING", "DIRTY")
        # Reset cached instance since state changed
        self._github_instance = None
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
        self._github_builder_state.pr_mergeability[pr_number] = (mergeable, merge_state)
        # Reset cached instance since state changed
        self._github_instance = None
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

    def with_no_branch(self) -> "FakeGtKitOps":
        """Configure state where current branch is empty/not determinable.

        Returns:
            Self for chaining
        """
        repo_root = Path(self._repo_root)
        self._git_current_branches[repo_root] = None
        self._git_instance = None
        return self

    def with_orphan_branch(self, branch: str) -> "FakeGtKitOps":
        """Configure an orphan branch (no parent tracking in Graphite).

        Args:
            branch: Branch name

        Returns:
            Self for chaining
        """
        repo_root = Path(self._repo_root)
        self._git_current_branches[repo_root] = branch
        # Don't configure trunk or parent - simulates orphan
        self._github_builder_state.current_branch = branch
        self._github_instance = None
        self._git_instance = None
        return self

    def with_merge_conflict(self, base_branch: str, head_branch: str) -> "FakeGtKitOps":
        """Configure git to simulate merge conflicts between branches.

        Args:
            base_branch: Base branch name
            head_branch: Head branch name

        Returns:
            Self for chaining
        """
        self._git_merge_conflicts[(base_branch, head_branch)] = True
        self._git_instance = None
        return self

    def with_trunk_branch(self, trunk: str) -> "FakeGtKitOps":
        """Set the trunk branch name (e.g., 'master' instead of 'main').

        Args:
            trunk: Trunk branch name

        Returns:
            Self for chaining
        """
        repo_root = Path(self._repo_root)
        self._git_trunk_branches[repo_root] = trunk
        self._git_instance = None
        return self

    def with_remote_url(self, url: str, remote: str = "origin") -> "FakeGtKitOps":
        """Set the URL for a git remote.

        Args:
            url: Remote URL (e.g., 'https://github.com/org/repo.git')
            remote: Remote name (default: 'origin')

        Returns:
            Self for chaining
        """
        repo_root = Path(self._repo_root)
        self._git_remote_urls[(repo_root, remote)] = url
        self._git_instance = None
        return self

    def with_conflicts(self, files: list[str]) -> "FakeGtKitOps":
        """Set conflicted files from git status.

        Args:
            files: List of file paths with conflicts

        Returns:
            Self for chaining
        """
        self._git_builder_state.conflicted_files = files
        self._git_builder_state.rebase_in_progress = True
        self._git_instance = None
        return self

    def with_rebase_in_progress(self, in_progress: bool = True) -> "FakeGtKitOps":
        """Set whether a rebase is in progress.

        Args:
            in_progress: Whether rebase is in progress

        Returns:
            Self for chaining
        """
        self._git_builder_state.rebase_in_progress = in_progress
        self._git_instance = None
        return self

    def with_continue_restack_failure(self, stderr: str = "") -> "FakeGtKitOps":
        """Configure continue_restack to fail.

        Args:
            stderr: Error message to include

        Returns:
            Self for chaining
        """
        # Configure main_graphite to raise RuntimeError for continue_restack
        existing_branches: dict[str, BranchMetadata] = {}
        if isinstance(self._main_graphite, FakeGraphite):
            existing_branches = self._main_graphite._branches
        error = RuntimeError(f"gt continue failed: {stderr}")
        self._main_graphite = FakeGraphite(
            continue_restack_raises=error,
            branches=existing_branches,
        )
        return self

    def with_clean_working_tree(self) -> "FakeGtKitOps":
        """Configure a clean working tree (no uncommitted changes).

        Returns:
            Self for chaining
        """
        repo_root = Path(self._repo_root)
        self._git_file_statuses[repo_root] = ([], [], [])  # All empty
        # Add to existing_paths so is_worktree_clean returns True
        self._git_builder_state.existing_paths.add(repo_root)
        self._git_instance = None
        return self
