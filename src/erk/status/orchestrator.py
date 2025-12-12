"""Orchestrator for collecting and assembling status information."""

import logging
from collections.abc import Callable
from pathlib import Path

from erk.core.context import ErkContext
from erk.status.collectors.base import StatusCollector
from erk.status.models.status_data import StatusData, WorktreeDisplayInfo
from erk_shared.integrations.parallel.abc import ParallelTaskRunner

logger = logging.getLogger(__name__)


class StatusOrchestrator:
    """Coordinates all status collectors and assembles final data.

    The orchestrator runs collectors in parallel with timeouts to ensure
    responsive output even if some collectors are slow or fail.
    """

    def __init__(
        self,
        collectors: list[StatusCollector],
        *,
        timeout_seconds: float = 2.0,
        runner: ParallelTaskRunner,
    ) -> None:
        """Create a status orchestrator.

        Args:
            collectors: List of status collectors to run
            timeout_seconds: Maximum time to wait for each collector (default: 2.0)
            runner: Parallel task runner for executing collectors
        """
        self.collectors = collectors
        self.timeout_seconds = timeout_seconds
        self.runner = runner

    def collect_status(self, ctx: ErkContext, worktree_path: Path, repo_root: Path) -> StatusData:
        """Collect all status information in parallel.

        Each collector runs in its own thread with a timeout. Failed or slow
        collectors will return None for their section.

        Args:
            ctx: Erk context with operations
            worktree_path: Path to the worktree
            repo_root: Path to repository root

        Returns:
            StatusData with all collected information
        """
        # Determine worktree info
        worktree_info = self._get_worktree_info(ctx, worktree_path, repo_root)

        # Build tasks for available collectors
        tasks: dict[str, Callable[[], object]] = {}
        for collector in self.collectors:
            if collector.is_available(ctx, worktree_path):
                # Create closure that captures current values
                def make_task(c=collector):
                    return lambda: c.collect(ctx, worktree_path, repo_root)

                tasks[collector.name] = make_task()

        # Run collectors in parallel via runner
        results = self.runner.run_parallel(tasks, self.timeout_seconds)

        # Get related worktrees
        related_worktrees = self._get_related_worktrees(ctx, repo_root, worktree_path)

        # Assemble StatusData - cast results to expected types
        # Results are either the correct type or None (from collector failures)
        from erk.status.models.status_data import (
            DependencyStatus,
            EnvironmentStatus,
            GitStatus,
            PlanStatus,
            PullRequestStatus,
            StackPosition,
        )

        git_result = results.get("git")
        stack_result = results.get("stack")
        pr_result = results.get("pr")
        env_result = results.get("environment")
        deps_result = results.get("dependencies")
        plan_result = results.get("plan")

        return StatusData(
            worktree_info=worktree_info,
            git_status=git_result if isinstance(git_result, GitStatus) else None,
            stack_position=stack_result if isinstance(stack_result, StackPosition) else None,
            pr_status=pr_result if isinstance(pr_result, PullRequestStatus) else None,
            environment=env_result if isinstance(env_result, EnvironmentStatus) else None,
            dependencies=deps_result if isinstance(deps_result, DependencyStatus) else None,
            plan=plan_result if isinstance(plan_result, PlanStatus) else None,
            related_worktrees=related_worktrees,
        )

    def _get_worktree_info(
        self, ctx: ErkContext, worktree_path: Path, repo_root: Path
    ) -> WorktreeDisplayInfo:
        """Get basic worktree information.

        Args:
            ctx: Erk context
            worktree_path: Path to worktree
            repo_root: Path to repository root

        Returns:
            WorktreeDisplayInfo with basic information
        """
        # Check paths exist before resolution to avoid OSError
        is_root = False
        if worktree_path.exists() and repo_root.exists():
            is_root = worktree_path.resolve() == repo_root.resolve()

        name = "root" if is_root else worktree_path.name
        branch = ctx.git.get_current_branch(worktree_path)

        return WorktreeDisplayInfo(name=name, path=worktree_path, branch=branch, is_root=is_root)

    def _get_related_worktrees(
        self, ctx: ErkContext, repo_root: Path, current_path: Path
    ) -> list[WorktreeDisplayInfo]:
        """Get list of other worktrees in the repository.

        Args:
            ctx: Erk context
            repo_root: Path to repository root
            current_path: Path to current worktree (excluded from results)

        Returns:
            List of WorktreeDisplayInfo for other worktrees
        """
        worktrees = ctx.git.list_worktrees(repo_root)

        # Check paths exist before resolution to avoid OSError
        if not current_path.exists():
            return []

        current_resolved = current_path.resolve()

        related = []
        for wt in worktrees:
            # Skip if worktree path doesn't exist
            if not wt.path.exists():
                continue

            wt_resolved = wt.path.resolve()

            # Skip current worktree
            if wt_resolved == current_resolved:
                continue

            # Determine if this is the root worktree
            is_root = False
            if repo_root.exists():
                is_root = wt_resolved == repo_root.resolve()

            name = "root" if is_root else wt.path.name

            related.append(
                WorktreeDisplayInfo(name=name, path=wt.path, branch=wt.branch, is_root=is_root)
            )

        return related
