"""Graphite submit strategy implementation.

This strategy encapsulates the Graphite-first flow where gt submit handles
both the push and PR creation, avoiding tracking divergence issues.
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.gateway.gt.abc import GtKit
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.strategy.abc import SubmitStrategy
from erk_shared.gateway.pr.strategy.types import (
    StrategyGenerator,
    SubmitStrategyError,
    SubmitStrategyResult,
)
from erk_shared.github.parsing import parse_git_remote_url
from erk_shared.github.types import GitHubRepoId, PRNotFound


@dataclass(frozen=True)
class GraphiteSubmitStrategy(SubmitStrategy):
    """Strategy that uses Graphite (gt submit) for PR submission.

    This strategy:
    1. Commits any uncommitted changes
    2. Runs gt submit to push and create/update PR
    3. Queries GitHub for PR info
    4. Computes parent branch and Graphite URL

    Use this strategy when Graphite is authenticated and the branch is tracked.
    It avoids the "tracking divergence" issue by letting Graphite control the push.
    """

    def execute(
        self,
        ops: GtKit,
        cwd: Path,
        *,
        force: bool,
    ) -> StrategyGenerator:
        """Execute Graphite-first PR submission flow."""
        repo_root = ops.git.get_repository_root(cwd)
        branch_name = ops.git.get_current_branch(cwd)

        # Check for detached HEAD state
        if branch_name is None:
            yield CompletionEvent(
                result=SubmitStrategyError(
                    error_type="detached-head",
                    message="Not on a branch (detached HEAD state)",
                    details={},
                )
            )
            return

        # Commit any uncommitted changes first
        if ops.git.has_uncommitted_changes(cwd):
            yield ProgressEvent(message="Committing uncommitted changes...", style="info")
            ops.git.add_all(cwd)
            ops.git.commit(cwd, "WIP: Prepare for PR submission")

        # Run gt submit
        yield ProgressEvent(message="Running gt submit...", style="info")
        try:
            ops.graphite.submit_stack(
                repo_root,
                publish=True,
                restack=False,
                quiet=False,
                force=force,
            )
        except RuntimeError as e:
            yield CompletionEvent(
                result=SubmitStrategyError(
                    error_type="graphite-submit-failed",
                    message=f"Graphite submit failed: {e}",
                    details={"error": str(e)},
                )
            )
            return

        yield ProgressEvent(message="Graphite submit completed", style="success")

        # Query GitHub to get PR info
        yield ProgressEvent(message="Getting PR info...", style="info")
        pr_info = ops.github.get_pr_for_branch(repo_root, branch_name)

        if isinstance(pr_info, PRNotFound):
            yield CompletionEvent(
                result=SubmitStrategyError(
                    error_type="pr-not-found",
                    message=(
                        f"PR not found for branch '{branch_name}' after gt submit.\n"
                        "This may happen if gt submit didn't create a PR. Try running:\n"
                        "  gt submit --publish"
                    ),
                    details={"branch": branch_name},
                )
            )
            return

        # Get parent branch for base_branch
        trunk_branch = ops.git.detect_trunk_branch(repo_root)
        parent_branch = (
            ops.branch_manager.get_parent_branch(Path(repo_root), branch_name) or trunk_branch
        )

        # Get Graphite URL
        remote_url = ops.git.get_remote_url(repo_root, "origin")
        owner, repo_name = parse_git_remote_url(remote_url)
        repo_id = GitHubRepoId(owner=owner, repo=repo_name)
        graphite_url = ops.graphite.get_graphite_url(repo_id, pr_info.number)

        yield ProgressEvent(message=f"PR #{pr_info.number} ready", style="success")

        yield CompletionEvent(
            result=SubmitStrategyResult(
                pr_number=pr_info.number,
                base_branch=parent_branch,
                graphite_url=graphite_url,
                pr_url=pr_info.url,
                branch_name=branch_name,
                was_created=True,  # gt submit creates or updates the PR
            )
        )
