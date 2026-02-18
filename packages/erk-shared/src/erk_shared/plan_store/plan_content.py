"""Plan content parsing and resolution utilities.

Pure functions for extracting information from plan markdown content
and resolving plan content from multiple sources with priority ordering.
"""

from pathlib import Path

from erk_shared.gateway.claude_installation.abc import ClaudeInstallation
from erk_shared.scratch.scratch import get_scratch_dir


def extract_title_from_plan(plan_content: str) -> str:
    """Extract title from plan content's first markdown heading.

    Args:
        plan_content: Plan markdown content

    Returns:
        Title text, or "Untitled Plan" if no heading found
    """
    for line in plan_content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return "Untitled Plan"


def resolve_plan_content(
    *,
    plan_file: Path | None,
    session_id: str | None,
    repo_root: Path,
    claude_installation: ClaudeInstallation,
    cwd: Path,
) -> str | None:
    """Resolve plan content from multiple sources with priority ordering.

    Priority: plan_file > scratch dir plan.md > claude_installation.get_latest_plan()

    Args:
        plan_file: Explicit plan file path (highest priority)
        session_id: Session ID for session-scoped lookup
        repo_root: Repository root for scratch directory
        claude_installation: ClaudeInstallation gateway for plan discovery
        cwd: Current working directory

    Returns:
        Plan content as string, or None if no plan found
    """
    if plan_file is not None:
        return plan_file.read_text(encoding="utf-8")

    if session_id is not None:
        scratch_dir = get_scratch_dir(session_id, repo_root=repo_root)
        scratch_plan_path = scratch_dir / "plan.md"
        if scratch_plan_path.exists():
            return scratch_plan_path.read_text(encoding="utf-8")

    return claude_installation.get_latest_plan(cwd, session_id=session_id)
