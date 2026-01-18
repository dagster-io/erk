"""Implementation folder collector."""

import logging
from pathlib import Path

from erk.core.context import ErkContext
from erk.status.collectors.base import StatusCollector
from erk.status.models.status_data import PlanStatus
from erk_shared.impl_folder import (
    get_impl_path,
    read_issue_reference,
)

logger = logging.getLogger(__name__)


class PlanFileCollector(StatusCollector):
    """Collects information about .impl/ folder."""

    @property
    def name(self) -> str:
        """Name identifier for this collector."""
        return "plan"

    def is_available(self, ctx: ErkContext, worktree_path: Path) -> bool:
        """Check if .impl/plan.md exists.

        Args:
            ctx: Erk context
            worktree_path: Path to worktree

        Returns:
            True if .impl/plan.md exists
        """
        impl_path = get_impl_path(worktree_path, git_ops=ctx.git)
        return impl_path is not None

    def collect(self, ctx: ErkContext, worktree_path: Path, repo_root: Path) -> PlanStatus | None:
        """Collect implementation folder information.

        Args:
            ctx: Erk context
            worktree_path: Path to worktree
            repo_root: Repository root path

        Returns:
            PlanStatus with folder information or None if collection fails
        """
        impl_path = get_impl_path(worktree_path, git_ops=ctx.git)

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
        impl_folder = worktree_path / ".impl"

        # Read issue reference if present
        issue_ref = read_issue_reference(impl_folder)
        issue_number = issue_ref.issue_number if issue_ref else None
        issue_url = issue_ref.issue_url if issue_ref else None

        return PlanStatus(
            exists=True,
            path=impl_folder,
            summary=summary,
            line_count=line_count,
            first_lines=first_lines,
            format="folder",
            issue_number=issue_number,
            issue_url=issue_url,
        )
