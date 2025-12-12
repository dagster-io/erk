"""Non-ideal state types and operations that return them.

This module provides:
- NonIdealState types (imported from erk_shared)
- GitHubChecks: Class with methods that return T | NonIdealState (never throws)

Usage:
    from erk.kits.cli_result import exit_with_error
    from erk.kits.non_ideal_state import GitHubChecks, BranchDetectionFailed

    # Methods return T | NonIdealState - inspect results without triggering exit
    result = GitHubChecks.branch(None)
    if isinstance(result, BranchDetectionFailed):
        exit_with_error(result.error_type, result.message)
    branch = result  # Type narrowed to str
"""

from pathlib import Path

from erk_shared.github.abc import GitHub
from erk_shared.github.issues.abc import GitHubIssues
from erk_shared.github.types import PRDetails, PRNotFound

# Re-export NonIdealState types from erk_shared
from erk_shared.non_ideal_state import (
    BranchDetectionFailed,
    GitHubAPIFailed,
    NonIdealState,
    NoPRForBranch,
    PRNotFoundError,
)

__all__ = [
    "NonIdealState",
    "BranchDetectionFailed",
    "NoPRForBranch",
    "PRNotFoundError",
    "GitHubAPIFailed",
    "GitHubChecks",
]


class GitHubChecks:
    """GitHub operations that return T | NonIdealState.

    This class never throws exceptions or exits. All error conditions are
    returned as NonIdealState objects, allowing callers to inspect and
    handle them as needed.

    For kit CLI commands that should exit on error, check isinstance() and
    call exit_with_error() from cli_result.py.
    """

    @staticmethod
    def branch(branch: str | None) -> str | BranchDetectionFailed:
        """Check if branch was detected.

        Args:
            branch: Branch name or None if detection failed

        Returns:
            The branch name if detected, or BranchDetectionFailed
        """
        if branch is None:
            return BranchDetectionFailed()
        return branch

    @staticmethod
    def pr_for_branch(
        github: GitHub,
        repo_root: Path,
        branch: str,
    ) -> PRDetails | NoPRForBranch:
        """Look up PR for branch.

        Args:
            github: GitHub interface
            repo_root: Repository root path
            branch: Branch name to look up

        Returns:
            PRDetails if found, or NoPRForBranch
        """
        pr_result = github.get_pr_for_branch(repo_root, branch)
        if isinstance(pr_result, PRNotFound):
            return NoPRForBranch(branch=branch)
        return pr_result

    @staticmethod
    def pr_by_number(
        github: GitHub,
        repo_root: Path,
        pr_number: int,
    ) -> PRDetails | PRNotFoundError:
        """Look up PR by number.

        Args:
            github: GitHub interface
            repo_root: Repository root path
            pr_number: PR number to look up

        Returns:
            PRDetails if found, or PRNotFoundError
        """
        pr_result = github.get_pr(repo_root, pr_number)
        if isinstance(pr_result, PRNotFound):
            return PRNotFoundError(pr_number=pr_number)
        return pr_result

    @staticmethod
    def add_reaction(
        github_issues: GitHubIssues,
        repo_root: Path,
        comment_id: int,
        reaction: str,
    ) -> None | GitHubAPIFailed:
        """Add reaction to a comment.

        Args:
            github_issues: GitHubIssues interface
            repo_root: Repository root path
            comment_id: Numeric comment ID
            reaction: Reaction type (+1, -1, laugh, etc.)

        Returns:
            None on success, or GitHubAPIFailed on error
        """
        try:
            github_issues.add_reaction_to_comment(repo_root, comment_id, reaction)
            return None
        except RuntimeError as e:
            return GitHubAPIFailed(_message=str(e))

    @staticmethod
    def issue_comments(
        github_issues: GitHubIssues,
        repo_root: Path,
        issue_number: int,
    ) -> list | GitHubAPIFailed:
        """Get issue/PR discussion comments.

        Args:
            github_issues: GitHubIssues interface
            repo_root: Repository root path
            issue_number: Issue or PR number

        Returns:
            List of comments on success, or GitHubAPIFailed on error
        """
        try:
            return github_issues.get_issue_comments_with_urls(repo_root, issue_number)
        except RuntimeError as e:
            return GitHubAPIFailed(_message=str(e))
