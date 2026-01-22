"""Graphite-first PR submit strategy.

This strategy uses `gt submit` for push and PR creation when:
1. Graphite is authenticated
2. The branch is tracked by Graphite

This avoids "tracking divergence" issues by letting Graphite control the push.
"""

from collections.abc import Generator
from pathlib import Path

from erk_shared.gateway.gt.abc import GtKit
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.strategy.abc import SubmitStrategy
from erk_shared.gateway.pr.strategy.types import SubmitStrategyError, SubmitStrategyResult
from erk_shared.github.parsing import construct_pr_url, parse_git_remote_url
from erk_shared.github.types import GitHubRepoId, PRNotFound


class GraphiteSubmitStrategy(SubmitStrategy):
    """Graphite-first submit strategy.

    Flow:
    1. Commit any uncommitted changes
    2. Run `gt submit` (handles push + PR creation)
    3. Query GitHub for PR info
    4. Compute Graphite URL
    5. Return SubmitStrategyResult

    Errors are returned as SubmitStrategyError instead of raising exceptions.
    """

    def execute(
        self,
        ops: GtKit,
        cwd: Path,
        *,
        force: bool,
    ) -> Generator[
        ProgressEvent | CompletionEvent[SubmitStrategyResult | SubmitStrategyError], None, None
    ]:
        """Execute Graphite-first submit flow."""
        repo_root = ops.git.get_repository_root(cwd)
        branch_name = ops.git.get_current_branch(cwd)

        # Check for detached HEAD
        if branch_name is None:
            yield CompletionEvent(
                result=SubmitStrategyError(
                    error_type="detached_head",
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

        # Run gt submit (handles push + PR creation)
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
                    error_type="gt_submit_failed",
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

        # Get parent branch for base_branch
        trunk_branch = ops.git.detect_trunk_branch(repo_root)
        parent_branch = ops.branch_manager.get_parent_branch(Path(repo_root), branch_name)
        base_branch = parent_branch if parent_branch is not None else trunk_branch

        # Get Graphite URL
        remote_url = ops.git.get_remote_url(repo_root, "origin")
        owner, repo_name = parse_git_remote_url(remote_url)
        repo_id = GitHubRepoId(owner=owner, repo=repo_name)
        graphite_url = ops.graphite.get_graphite_url(repo_id, pr_info.number)

        # Construct PR URL
        pr_url = construct_pr_url(owner, repo_name, pr_info.number)

        yield ProgressEvent(message=f"PR #{pr_info.number} ready", style="success")

        yield CompletionEvent(
            result=SubmitStrategyResult(
                pr_number=pr_info.number,
                base_branch=base_branch,
                graphite_url=graphite_url,
                pr_url=pr_url,
                branch_name=branch_name,
                was_created=True,  # gt submit creates if needed
            )
        )
