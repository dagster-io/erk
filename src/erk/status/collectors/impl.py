"""Implementation folder collector."""

import logging
from pathlib import Path

from erk.core.context import ErkContext
from erk.status.collectors.base import StatusCollector
from erk.status.models.status_data import PlanStatus
from erk_shared.impl_folder import (
    get_impl_dir,
    get_impl_path,
    read_plan_ref,
)

logger = logging.getLogger(__name__)


class PlanFileCollector(StatusCollector):
    """Collects information about .erk/impl-context/ folder."""

    @property
    def name(self) -> str:
        """Name identifier for this collector."""
        return "plan"

    def is_available(self, ctx: ErkContext, worktree_path: Path) -> bool:
        """Check if plan.md exists in .erk/impl-context/ directory.

        Args:
            ctx: Erk context
            worktree_path: Path to worktree

        Returns:
            True if plan.md exists in .erk/impl-context/
        """
        branch = ctx.git.branch.get_current_branch(worktree_path)
        if branch is None:
            return False
        impl_path = get_impl_path(worktree_path, branch_name=branch, git_ops=ctx.git)
        return impl_path is not None

    def collect(self, ctx: ErkContext, worktree_path: Path, repo_root: Path) -> PlanStatus | None:
        """Collect .erk/impl-context/ folder information.

        Args:
            ctx: Erk context
            worktree_path: Path to worktree
            repo_root: Repository root path

        Returns:
            PlanStatus with folder information or None if collection fails
        """
        branch = ctx.git.branch.get_current_branch(worktree_path)
        if branch is None:
            return PlanStatus(
                exists=False,
                path=None,
                summary=None,
                line_count=0,
                first_lines=[],
                format="none",
            )

        impl_path = get_impl_path(worktree_path, branch_name=branch, git_ops=ctx.git)

        if impl_path is None:
            return PlanStatus(
                exists=False,
                path=None,
                summary=None,
                line_count=0,
                first_lines=[],
                format="none",
            )

        # Read plan.md
        content = impl_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        line_count = len(lines)

        # Get first 5 lines
        first_lines = lines[:5] if len(lines) >= 5 else lines

        # Extract summary from first few non-empty lines
        summary_lines = []
        for line in lines[:10]:  # Look at first 10 lines
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                summary_lines.append(stripped)
                if len(summary_lines) >= 2:
                    break

        summary = " ".join(summary_lines) if summary_lines else None

        # Truncate summary if too long
        if summary and len(summary) > 100:
            summary = summary[:97] + "..."

        # Return folder path, not plan.md file path
        impl_folder = get_impl_dir(worktree_path, branch_name=branch)

        # Read plan reference if present
        plan_ref = read_plan_ref(impl_folder)
        pr_number = int(plan_ref.pr_id) if plan_ref else None
        pr_url = plan_ref.url if plan_ref else None

        return PlanStatus(
            exists=True,
            path=impl_folder,
            summary=summary,
            line_count=line_count,
            first_lines=first_lines,
            format="folder",
            pr_number=pr_number,
            pr_url=pr_url,
        )
