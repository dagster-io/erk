"""Data models for status information."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorktreeDisplayInfo:
    """Worktree information for display/presentation purposes.

    This represents worktree data for status rendering and display.
    For infrastructure-layer worktree data, see erk.core.gitops.WorktreeInfo.
    """

    name: str
    path: Path
    branch: str | None
    is_root: bool

    @staticmethod
    def root(path: Path, branch: str = "main", name: str = "root") -> WorktreeDisplayInfo:
        """Create root worktree for test display.

        Args:
            path: Path to the root worktree
            branch: Branch name (default: "main")
            name: Display name (default: "root")

        Returns:
            WorktreeDisplayInfo with is_root=True

        Example:
            Before (4 lines):
                worktree = WorktreeDisplayInfo(
                    name="root", path=repo_root, branch="main", is_root=True
                )

            After (1 line):
                worktree = WorktreeDisplayInfo.root(repo_root)
        """
        return WorktreeDisplayInfo(path=path, branch=branch, is_root=True, name=name)

    @staticmethod
    def feature(path: Path, branch: str, name: str | None = None) -> WorktreeDisplayInfo:
        """Create feature worktree for test display.

        Args:
            path: Path to the feature worktree
            branch: Branch name
            name: Display name (default: uses path.name)

        Returns:
            WorktreeDisplayInfo with is_root=False

        Example:
            Before (4 lines):
                worktree = WorktreeDisplayInfo(
                    name="my-feature", path=feature_wt, branch="feature", is_root=False
                )

            After (1 line):
                worktree = WorktreeDisplayInfo.feature(feature_wt, "feature")
        """
        display_name = name if name else path.name
        return WorktreeDisplayInfo(path=path, branch=branch, is_root=False, name=display_name)


@dataclass(frozen=True)
class CommitInfo:
    """Information about a git commit."""

    sha: str
    message: str
    author: str
    date: str

    @staticmethod
    def test_commit(
        sha: str = "abc1234",
        message: str = "Test commit",
        author: str = "Test User",
        date: str = "1 hour ago",
    ) -> CommitInfo:
        """Create a commit for tests with sensible defaults.

        Args:
            sha: Commit SHA (default: "abc1234")
            message: Commit message (default: "Test commit")
            author: Commit author (default: "Test User")
            date: Commit date (default: "1 hour ago")

        Returns:
            CommitInfo with all fields populated

        Example:
            Before (5 lines):
                recent_commits = [
                    CommitInfo(sha="abc1234", message="Initial commit",
                               author="Test User", date="1 hour ago"),
                ]

            After (1 line):
                recent_commits = [CommitInfo.test_commit()]
        """
        return CommitInfo(sha=sha, message=message, author=author, date=date)


@dataclass(frozen=True)
class GitStatus:
    """Git repository status information."""

    branch: str | None
    clean: bool
    ahead: int
    behind: int
    staged_files: list[str]
    modified_files: list[str]
    untracked_files: list[str]
    recent_commits: list[CommitInfo]

    @staticmethod
    def clean_status(branch: str, ahead: int = 0, behind: int = 0) -> GitStatus:
        """Create clean status (no changes) for tests.

        Args:
            branch: Branch name
            ahead: Commits ahead of remote (default: 0)
            behind: Commits behind remote (default: 0)

        Returns:
            GitStatus with clean=True and empty file lists

        Example:
            Before (8 lines):
                status = GitStatus(
                    branch="test",
                    clean=True,
                    ahead=0,
                    behind=0,
                    staged_files=[],
                    modified_files=[],
                    untracked_files=[],
                    recent_commits=[],
                )

            After (1 line):
                status = GitStatus.clean_status("test")
        """
        return GitStatus(
            branch=branch,
            clean=True,
            ahead=ahead,
            behind=behind,
            staged_files=[],
            modified_files=[],
            untracked_files=[],
            recent_commits=[],
        )

    @staticmethod
    def dirty_status(
        branch: str,
        *,
        modified: list[str] | None = None,
        staged: list[str] | None = None,
        untracked: list[str] | None = None,
        ahead: int = 0,
        behind: int = 0,
    ) -> GitStatus:
        """Create dirty status (with changes) for tests.

        Args:
            branch: Branch name
            modified: Modified files (default: [])
            staged: Staged files (default: [])
            untracked: Untracked files (default: [])
            ahead: Commits ahead of remote (default: 0)
            behind: Commits behind remote (default: 0)

        Returns:
            GitStatus with clean=False and specified file lists

        Example:
            Before (9 lines):
                status = GitStatus(
                    branch="feature",
                    clean=False,
                    ahead=0,
                    behind=0,
                    staged_files=[],
                    modified_files=["file.py"],
                    untracked_files=[],
                    recent_commits=[],
                )

            After (1 line):
                status = GitStatus.dirty_status("feature", modified=["file.py"])
        """
        return GitStatus(
            branch=branch,
            clean=False,
            ahead=ahead,
            behind=behind,
            staged_files=staged or [],
            modified_files=modified or [],
            untracked_files=untracked or [],
            recent_commits=[],
        )

    @staticmethod
    def with_commits(branch: str, commits: list[CommitInfo], clean: bool = True) -> GitStatus:
        """Create status with commit history for tests.

        Args:
            branch: Branch name
            commits: List of recent commits
            clean: Whether working tree is clean (default: True)

        Returns:
            GitStatus with commits populated

        Example:
            Before (9 lines):
                status = GitStatus(
                    branch="main",
                    clean=True,
                    ahead=0,
                    behind=0,
                    staged_files=[],
                    modified_files=[],
                    untracked_files=[],
                    recent_commits=[commit1, commit2],
                )

            After (1 line):
                status = GitStatus.with_commits("main", [commit1, commit2])
        """
        return GitStatus(
            branch=branch,
            clean=clean,
            ahead=0,
            behind=0,
            staged_files=[],
            modified_files=[],
            untracked_files=[],
            recent_commits=commits,
        )


@dataclass(frozen=True)
class StackPosition:
    """Worktree stack position information."""

    stack: list[str]
    current_branch: str
    parent_branch: str | None
    children_branches: list[str]
    is_trunk: bool


@dataclass(frozen=True)
class PullRequestStatus:
    """Pull request status information."""

    number: int
    title: str | None  # May not be available from all data sources
    state: str
    is_draft: bool
    url: str
    checks_passing: bool | None
    reviews: list[str] | None  # May not be available from all data sources
    ready_to_merge: bool


@dataclass(frozen=True)
class EnvironmentStatus:
    """Environment variables status."""

    variables: dict[str, str]


@dataclass(frozen=True)
class DependencyStatus:
    """Dependency status for various language ecosystems."""

    language: str
    up_to_date: bool
    outdated_count: int
    details: str | None


@dataclass(frozen=True)
class PlanStatus:
    """Status of .impl/ folder and enriched plans."""

    exists: bool
    path: Path | None
    summary: str | None
    line_count: int
    first_lines: list[str]
    format: str  # "folder" or "none"
    enriched_plan_path: Path | None = None  # Path to enriched plan file
    enriched_plan_filename: str | None = None  # Filename of enriched plan
    issue_number: int | None = None  # GitHub issue number if linked
    issue_url: str | None = None  # GitHub issue URL if linked


@dataclass(frozen=True)
class StatusData:
    """Container for all status information."""

    worktree_info: WorktreeDisplayInfo
    git_status: GitStatus | None
    stack_position: StackPosition | None
    pr_status: PullRequestStatus | None
    environment: EnvironmentStatus | None
    dependencies: DependencyStatus | None
    plan: PlanStatus | None
    related_worktrees: list[WorktreeDisplayInfo]

    @staticmethod
    def minimal(worktree_info: WorktreeDisplayInfo) -> StatusData:
        """Create minimal status data (all optional fields None) for tests.

        Args:
            worktree_info: Worktree display information

        Returns:
            StatusData with only worktree_info set, all other fields None/empty

        Example:
            Before (9 lines):
                status_data = StatusData(
                    worktree_info=WorktreeDisplayInfo(
                        name="my-feature", path=wt_path, branch="feature", is_root=False
                    ),
                    git_status=None,
                    stack_position=None,
                    pr_status=None,
                    environment=None,
                    dependencies=None,
                    plan=None,
                    related_worktrees=[],
                )

            After (2 lines):
                worktree_info = WorktreeDisplayInfo.feature(wt_path, "feature")
                status_data = StatusData.minimal(worktree_info)
        """
        return StatusData(
            worktree_info=worktree_info,
            git_status=None,
            stack_position=None,
            pr_status=None,
            environment=None,
            dependencies=None,
            plan=None,
            related_worktrees=[],
        )

    @staticmethod
    def with_git_status(worktree_info: WorktreeDisplayInfo, git_status: GitStatus) -> StatusData:
        """Create status data with git status populated.

        Args:
            worktree_info: Worktree display information
            git_status: Git status information

        Returns:
            StatusData with worktree_info and git_status set, other fields None/empty

        Example:
            Before (11 lines):
                status_data = StatusData(
                    worktree_info=WorktreeDisplayInfo(
                        name="root", path=repo_root, branch="main", is_root=True
                    ),
                    git_status=GitStatus.clean_status("main"),
                    stack_position=None,
                    pr_status=None,
                    environment=None,
                    dependencies=None,
                    plan=None,
                    related_worktrees=[],
                )

            After (2 lines):
                worktree_info = WorktreeDisplayInfo.root(repo_root)
                status_data = StatusData.with_git_status(
                    worktree_info, GitStatus.clean_status("main")
                )
        """
        return StatusData(
            worktree_info=worktree_info,
            git_status=git_status,
            stack_position=None,
            pr_status=None,
            environment=None,
            dependencies=None,
            plan=None,
            related_worktrees=[],
        )
