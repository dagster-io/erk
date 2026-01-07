"""GitHub PR collector."""

from pathlib import Path

from erk.core.context import ErkContext
from erk.status.collectors.base import StatusCollector
from erk.status.models.status_data import PullRequestStatus


class GitHubPRCollector(StatusCollector):
    """Collects GitHub pull request information."""

    @property
    def name(self) -> str:
        """Name identifier for this collector."""
        return "pr"

    def is_available(self, ctx: ErkContext, worktree_path: Path) -> bool:
        """Check if PR information should be fetched.

        Args:
            ctx: Erk context
            worktree_path: Path to worktree

        Returns:
            True if worktree exists
        """
        return worktree_path.exists()

    def collect(
        self, ctx: ErkContext, worktree_path: Path, repo_root: Path
    ) -> PullRequestStatus | None:
        """Collect GitHub PR information.

        Args:
            ctx: Erk context
            worktree_path: Path to worktree
            repo_root: Repository root path

        Returns:
            PullRequestStatus with PR information or None if collection fails
        """
        branch = ctx.git.get_current_branch(worktree_path)
        if branch is None:
            return None

        # Always use Graphite (fast, no pagination issues)
        prs = ctx.graphite.get_prs_from_graphite(ctx.git, repo_root)

        # Fail fast if Graphite cache unavailable - no fallback to GitHub
        if not prs:
            return None

        # Find PR for current branch
        pr = prs.get(branch)
        if pr is None:
            return None

        # Determine if ready to merge
        ready_to_merge = (
            pr.state == "OPEN"
            and not pr.is_draft
            and (pr.checks_passing is True or pr.checks_passing is None)
        )

        return PullRequestStatus(
            number=pr.number,
            title=None,  # Title not available in PullRequestInfo
            state=pr.state,
            is_draft=pr.is_draft,
            url=pr.url,
            checks_passing=pr.checks_passing,
            reviews=None,  # Reviews not available in PullRequestInfo
            ready_to_merge=ready_to_merge,
        )
