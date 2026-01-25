"""Graphite-first PR submission strategy.

This strategy uses Graphite's gt submit to handle push and PR creation.
It is used when Graphite is authenticated and the branch is tracked,
avoiding "tracking divergence" by letting Graphite control the push.
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.context.context import ErkContext
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.strategy.abc import StrategyGenerator, SubmitStrategy
from erk_shared.gateway.pr.strategy.types import SubmitStrategyError, SubmitStrategyResult
from erk_shared.github.parsing import parse_git_remote_url
from erk_shared.github.types import GitHubRepoId, PRNotFound


@dataclass(frozen=True)
class GraphiteSubmitStrategy(SubmitStrategy):
    """Strategy using Graphite's gt submit for PR submission.

    This strategy delegates push and PR creation to gt submit, then queries
    GitHub to get PR information. Use this when:
    - Graphite is authenticated
    - The branch is tracked by Graphite

    The strategy handles the complete flow:
    1. Run gt submit (handles push + PR creation)
    2. Query GitHub for PR info
    3. Compute Graphite URL
    """

    def execute(
        self,
        ctx: ErkContext,
        cwd: Path,
        *,
        force: bool,
    ) -> StrategyGenerator:
        """Execute Graphite-first PR submission.

        Args:
            ctx: ErkContext providing git, github, and graphite operations
            cwd: Working directory
            force: If True, force push

        Yields:
            ProgressEvent for status updates
            CompletionEvent with SubmitStrategyResult or SubmitStrategyError
        """
        repo_root = ctx.git.get_repository_root(cwd)
        branch_name = ctx.git.get_current_branch(cwd)

        if branch_name is None:
            yield CompletionEvent(
                SubmitStrategyError(
                    status="error",
                    error_type="no_branch",
                    message="Not on a branch (detached HEAD state)",
                    details={},
                )
            )
            return

        # Step 1: Run gt submit
        yield ProgressEvent("Running gt submit...")
        try:
            ctx.graphite.submit_stack(
                repo_root,
                publish=True,
                restack=False,
                quiet=False,
                force=force,
            )
        except RuntimeError as e:
            yield CompletionEvent(
                SubmitStrategyError(
                    status="error",
                    error_type="graphite_submit_failed",
                    message=f"Graphite submit failed: {e}",
                    details={"branch": branch_name, "error": str(e)},
                )
            )
            return
        yield ProgressEvent("Graphite submit completed", style="success")

        # Step 2: Query GitHub for PR info
        yield ProgressEvent("Getting PR info...")
        pr_info = ctx.github.get_pr_for_branch(repo_root, branch_name)
        if isinstance(pr_info, PRNotFound):
            yield CompletionEvent(
                SubmitStrategyError(
                    status="error",
                    error_type="pr_not_found",
                    message=(
                        f"PR not found for branch '{branch_name}' after gt submit.\n"
                        "This may happen if gt submit didn't create a PR. Try running:\n"
                        "  gt submit --publish"
                    ),
                    details={"branch": branch_name},
                )
            )
            return

        # Step 3: Get parent branch for base_branch
        trunk_branch = ctx.git.detect_trunk_branch(repo_root)
        parent_branch = (
            ctx.branch_manager.get_parent_branch(Path(repo_root), branch_name) or trunk_branch
        )

        # Step 4: Get Graphite URL
        remote_url = ctx.git.get_remote_url(repo_root, "origin")
        owner, repo_name = parse_git_remote_url(remote_url)
        repo_id = GitHubRepoId(owner=owner, repo=repo_name)
        graphite_url = ctx.graphite.get_graphite_url(repo_id, pr_info.number)

        yield ProgressEvent(f"PR #{pr_info.number} ready", style="success")

        yield CompletionEvent(
            SubmitStrategyResult(
                status="success",
                pr_number=pr_info.number,
                base_branch=parent_branch,
                graphite_url=graphite_url,
                pr_url=pr_info.url,
                branch_name=branch_name,
                was_created=True,  # gt submit always creates/updates
            )
        )
