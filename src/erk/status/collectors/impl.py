"""Implementation folder collector."""

from pathlib import Path

import frontmatter

from erk.core.context import ErkContext
from erk.status.collectors.base import StatusCollector
from erk.status.models.status_data import PlanStatus
from erk_shared.impl_folder import (
    get_impl_path,
    get_progress_path,
    parse_progress_frontmatter,
    read_issue_reference,
)


def detect_enriched_plan(repo_root: Path) -> tuple[Path | None, str | None]:
    """Detect enriched plan file at repository root.

    Scans for *-plan.md files and checks for erk_plan marker.

    Args:
        repo_root: Repository root path

    Returns:
        Tuple of (path, filename) or (None, None) if not found
    """
    if not repo_root.exists():
        return None, None

    # Find all *-plan.md files
    plan_files = list(repo_root.glob("*-plan.md"))

    if not plan_files:
        return None, None

    # Sort by modification time (most recent first)
    plan_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    # Check each file for enrichment marker
    for plan_file in plan_files:
        # Use frontmatter library to parse YAML frontmatter
        post = frontmatter.load(str(plan_file))

        # Check for enrichment marker (handles missing frontmatter gracefully)
        if post.get("erk_plan") is True:
            return plan_file, plan_file.name

    return None, None


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

        # Detect enriched plan at repo root
        enriched_plan_path, enriched_plan_filename = detect_enriched_plan(repo_root)

        if impl_path is None:
            return PlanStatus(
                exists=False,
                path=None,
                summary=None,
                line_count=0,
                first_lines=[],
                progress_summary=None,
                format="none",
                enriched_plan_path=enriched_plan_path,
                enriched_plan_filename=enriched_plan_filename,
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

        # Calculate progress from progress.md
        progress_summary, completion_percentage = self._calculate_progress(worktree_path)

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
            progress_summary=progress_summary,
            format="folder",
            completion_percentage=completion_percentage,
            enriched_plan_path=enriched_plan_path,
            enriched_plan_filename=enriched_plan_filename,
            issue_number=issue_number,
            issue_url=issue_url,
        )

    def _calculate_progress(self, worktree_path: Path) -> tuple[str | None, int | None]:
        """Calculate progress from progress.md YAML frontmatter.

        The YAML steps array is the source of truth for progress tracking.
        Checkboxes are rendered output only.

        Args:
            worktree_path: Path to worktree

        Returns:
            Tuple of (progress_summary, completion_percentage)
            - progress_summary: String like "3/10 steps completed" or None
            - completion_percentage: Integer 0-100 or None if no YAML steps array
        """
        progress_path = get_progress_path(worktree_path)
        if progress_path is None:
            return None, None

        content = progress_path.read_text(encoding="utf-8")

        # Parse front matter
        front_matter = parse_progress_frontmatter(content)

        if front_matter is None:
            return None, None

        # Check for steps array (new format)
        if "steps" in front_matter and isinstance(front_matter["steps"], list):
            # New format: Read from YAML steps array (source of truth)
            steps = front_matter["steps"]
            total = len(steps)
            if total == 0:
                return None, None

            completed = sum(1 for step in steps if step.get("completed", False))
            completion_percentage = int((completed / total) * 100)
            progress_summary = f"{completed}/{total} steps completed"
            return progress_summary, completion_percentage

        # Old format fallback: Read from completed_steps/total_steps fields
        if "completed_steps" in front_matter and "total_steps" in front_matter:
            completed = front_matter.get("completed_steps", 0)
            total = front_matter.get("total_steps", 0)

            if total == 0:
                return None, None

            completion_percentage = int((completed / total) * 100)
            progress_summary = f"{completed}/{total} steps completed"
            return progress_summary, completion_percentage

        return None, None
